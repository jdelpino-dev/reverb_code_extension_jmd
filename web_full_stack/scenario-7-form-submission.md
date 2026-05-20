# Scenario 7: Form Submission (POST Request)

## The Ask

> "Add a 'Contact Seller' form on the listing detail page that POSTs a message."

This is the first write operation in the codebase. Tests POST handling, form validation, CSRF awareness, and the Post-Redirect-Get pattern.

______________________________________________________________________

## Phase 1: Explain the Architecture (2-3 min)

**What to say:**

"Everything in this codebase is read-only GET requests right now. Adding a POST form introduces new concerns: CSRF protection, input validation, what to show after submission, and how to handle errors without losing the user's input. I'll add a form to the listing detail page, a new POST route to handle submission, and implement the PRG pattern — Post, then Redirect on success to avoid double-submission on refresh."

**Clarifying questions:**

- "Should the message actually hit a Reverb API endpoint, or just simulate the flow?"
- "Do we need server-side validation (e.g., message can't be empty), or is client-side sufficient?"
- "After success, redirect back to the listing with a flash message, or to a confirmation page?"

______________________________________________________________________

## Phase 2: Implement

### 2a. Add the Form Template

**Python** — `templates/listing_detail.html` (add below existing content):

```html
{% block content %}
<!-- ... existing listing detail ... -->

<h2>Contact Seller</h2>
<form method="POST" action="{{ url_for('contact_seller', listing_id=listing['id']) }}">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

  <label for="message">Message:</label>
  <textarea id="message" name="message" required minlength="10"
    placeholder="Ask about this item...">{{ form_data.get('message', '') }}</textarea>

  <label for="email">Your email:</label>
  <input type="email" id="email" name="email" required
    value="{{ form_data.get('email', '') }}">

  <button type="submit">Send Message</button>
</form>

{% if errors %}
<div class="alert alert-danger">
  {% for error in errors %}
    <p>{{ error }}</p>
  {% endfor %}
</div>
{% endif %}
{% endblock %}
```

**Ruby** — `app/views/listings/show.html.erb`:

```erb
<h2>Contact Seller</h2>
<%= form_with url: contact_seller_listing_path(@listing['id']), method: :post, local: true do |f| %>
  <%= f.label :message %>
  <%= f.text_area :message, required: true, minlength: 10 %>

  <%= f.label :email, "Your email" %>
  <%= f.email_field :email, required: true %>

  <%= f.submit "Send Message" %>
<% end %>

<% if flash[:alert] %>
  <div class="alert alert-danger"><%= flash[:alert] %></div>
<% end %>
<% if flash[:notice] %>
  <div class="alert alert-success"><%= flash[:notice] %></div>
<% end %>
```

**React** — `ListingDetailPage.js` (add form component):

```jsx
function ContactForm({ listingId }) {
  const [message, setMessage] = useState('');
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState(null); // null | 'sending' | 'success' | 'error'
  const [errors, setErrors] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationErrors = validate(message, email);
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }
    setStatus('sending');
    try {
      await API.contactSeller(listingId, { message, email });
      setStatus('success');
      setMessage('');
      setEmail('');
    } catch {
      setStatus('error');
    }
  };

  // render form with status feedback
}

function validate(message, email) {
  const errors = [];
  if (message.trim().length < 10) errors.push('Message must be at least 10 characters.');
  if (!email.includes('@')) errors.push('Please enter a valid email.');
  return errors;
}
```

### 2b. Add POST Route

### Important: No Public Contact Endpoint Exists

The Reverb API has no public "contact seller" endpoint. The authenticated API exposes `_links.make_offer` (POST) for offers and `start_conversation` for messaging — both require Bearer tokens. In this exercise, we're **simulating the form-handling pattern** (POST, validate, PRG) without actually hitting a real API endpoint. Mention this to the interviewer: "There's no public contact endpoint, so I'm demonstrating the POST flow pattern — in production this would hit an authenticated messaging API."

**Python** — `app.py`:

```python
from flask import redirect, url_for, flash

@app.route('/listings/<listing_id>/contact', methods=['POST'])
def contact_seller(listing_id):
    message = request.form.get('message', '').strip()
    email = request.form.get('email', '').strip()

    errors = _validate_contact_form(message, email)
    if errors:
        # Re-render with errors — don't redirect (user keeps their input)
        listing = ReverbClient().listing(listing_id)
        return render_template('listing_detail.html',
            listing=listing,
            errors=errors,
            form_data={'message': message, 'email': email}
        ), 422

    # In production: send message via API or queue
    # ReverbClient().send_message(listing_id, message, email)

    flash("Message sent successfully!")
    return redirect(url_for('listing_detail', listing_id=listing_id))


def _validate_contact_form(message, email):
    errors = []
    if len(message) < 10:
        errors.append("Message must be at least 10 characters.")
    if '@' not in email:
        errors.append("Please enter a valid email address.")
    return errors
```

**Ruby** — `config/routes.rb`:

```ruby
resources :listings, only: [:index, :show] do
  post :contact_seller, on: :member
end
```

**Ruby** — `app/controllers/listings_controller.rb`:

```ruby
def contact_seller
  message = params[:message].to_s.strip
  email = params[:email].to_s.strip

  errors = validate_contact(message, email)
  if errors.any?
    @listing = ReverbClient.new.listing(params[:id])
    flash.now[:alert] = errors.join(', ')
    render :show, status: :unprocessable_entity
    return
  end

  # In production: ReverbClient.new.send_message(params[:id], message, email)
  flash[:notice] = "Message sent successfully!"
  redirect_to listing_path(params[:id])
end

private

def validate_contact(message, email)
  errors = []
  errors << "Message must be at least 10 characters." if message.length < 10
  errors << "Please enter a valid email address." unless email.include?('@')
  errors
end
```

### 2c. Key Patterns to Narrate

1. **Post-Redirect-Get (PRG):** On success, redirect (302) so refreshing doesn't re-submit. On validation failure, re-render (422) with errors and preserved input.
2. **CSRF protection:** Hidden token prevents cross-site form forgery. Flask-WTF adds this; Rails includes it by default.
3. **Server-side validation:** Never trust client-side validation alone — it can be bypassed.
4. **Re-rendering with state:** On error, pass form data back to the template so the user doesn't lose their input.

______________________________________________________________________

## Phase 3: Test

**Python** — `tests/test_contact_seller.py`:

```python
def test_successful_submission_redirects(client):
    with patch('reverb_client.requests.get'):
        res = client.post('/listings/123/contact', data={
            'message': 'Is this still available? I am very interested.',
            'email': 'buyer@example.com'
        })
    assert res.status_code == 302
    assert '/listings/123' in res.headers['Location']


def test_short_message_shows_error(client):
    with patch('reverb_client.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            'listing': {'id': '123', 'title': 'Test'}
        }
        res = client.post('/listings/123/contact', data={
            'message': 'Hi',
            'email': 'buyer@example.com'
        })
    assert res.status_code == 422
    html = parse_html(res)
    assert 'at least 10 characters' in html.body.text


def test_invalid_email_shows_error(client):
    with patch('reverb_client.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            'listing': {'id': '123', 'title': 'Test'}
        }
        res = client.post('/listings/123/contact', data={
            'message': 'Is this available? Would love to buy it.',
            'email': 'not-an-email'
        })
    assert res.status_code == 422
    html = parse_html(res)
    assert 'valid email' in html.body.text


def test_preserves_input_on_error(client):
    with patch('reverb_client.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            'listing': {'id': '123', 'title': 'Test'}
        }
        res = client.post('/listings/123/contact', data={
            'message': 'Hi',
            'email': 'buyer@example.com'
        })
    html = parse_html(res)
    textarea = html.find('textarea', {'name': 'message'})
    assert 'Hi' in textarea.text
```

**Ruby** — `spec/requests/listings_spec.rb`:

```ruby
describe "POST /listings/:id/contact_seller" do
  context "with valid data" do
    it "redirects to the listing" do
      post contact_seller_listing_path(id: '123'),
        params: { message: 'Is this still available?', email: 'test@example.com' }
      expect(response).to redirect_to(listing_path(id: '123'))
      follow_redirect!
      assert_select ".alert-success", /Message sent/
    end
  end

  context "with invalid data" do
    before do
      allow(ReverbClient).to receive(:new)
        .and_return(instance_double(ReverbClient, listing: { 'id' => '123', 'title' => 'Test' }))
    end

    it "re-renders with errors" do
      post contact_seller_listing_path(id: '123'),
        params: { message: 'Hi', email: 'bad' }
      expect(response).to have_http_status(:unprocessable_entity)
      assert_select ".alert-danger"
    end
  end
end
```

**React**:

```jsx
it('shows success message after valid submission', async () => {
  jest.spyOn(API, 'contactSeller').mockResolvedValue({});
  render(<ContactForm listingId="123" />);

  fireEvent.change(screen.getByLabelText(/message/i), {
    target: { value: 'Is this still available? Very interested.' }
  });
  fireEvent.change(screen.getByLabelText(/email/i), {
    target: { value: 'buyer@example.com' }
  });
  fireEvent.click(screen.getByText(/send message/i));

  await waitFor(() => {
    expect(screen.getByText(/success/i)).toBeInTheDocument();
  });
});

it('shows validation errors for short message', () => {
  render(<ContactForm listingId="123" />);
  fireEvent.change(screen.getByLabelText(/message/i), { target: { value: 'Hi' } });
  fireEvent.click(screen.getByText(/send message/i));
  expect(screen.getByText(/at least 10 characters/i)).toBeInTheDocument();
});
```

______________________________________________________________________

## Phase 4: Trade-off Discussion Points

- **Why PRG?** Without it, browser refresh re-submits the form. Users get "do you want to resubmit?" dialogs. PRG prevents duplicate submissions.
- **Client-side vs server-side validation?** Both. Client-side for instant UX feedback; server-side because client validation can be bypassed (disable JS, curl, bots).
- **CSRF in a SPA?** React apps don't use form-based CSRF tokens. Instead: SameSite cookies, custom headers (e.g., `X-Requested-With`), or token-in-header pattern.
- **What about spam?** Rate limiting, honeypot fields, reCAPTCHA. Not interview scope but worth mentioning.
- **422 vs 400?** 422 (Unprocessable Entity) means "I understood your request but the data is invalid." 400 means "I couldn't even parse your request." For validation errors, 422 is more precise.
- **Would you use a form library?** Flask-WTF (Python) or `form_with` (Rails) give you CSRF, validation, and error rendering for free. For this scope, manual is fine to show understanding.
