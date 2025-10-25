/**
 * JavaScript for Daily Stoic Reflection subscription form
 */

// Replace this with your actual API Gateway URL after deployment
const API_URL = 'API_GATEWAY_URL_HERE'; // e.g., 'https://abc123.execute-api.us-west-2.amazonaws.com/prod'

document.getElementById('subscribeForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const submitBtn = document.getElementById('submitBtn');
    const messageDiv = document.getElementById('message');
    const emailInput = document.getElementById('email');
    const honeypot = document.getElementById('website');

    // Check honeypot field (anti-bot)
    if (honeypot.value) {
        console.log('Bot detected');
        return;
    }

    const email = emailInput.value.trim();

    // Validate email
    if (!email || !isValidEmail(email)) {
        showMessage('Please enter a valid email address', 'error');
        return;
    }

    // Disable button and show loading state
    submitBtn.disabled = true;
    submitBtn.textContent = 'Subscribing...';
    messageDiv.style.display = 'none';

    try {
        const response = await fetch(`${API_URL}/api/subscribe`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: email })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showMessage(
                'Success! Please check your email to confirm your subscription.',
                'success'
            );
            emailInput.value = ''; // Clear the form
        } else {
            const errorMsg = data.error || 'Subscription failed. Please try again.';
            showMessage(errorMsg, 'error');
        }
    } catch (error) {
        console.error('Subscription error:', error);
        showMessage(
            'Network error. Please check your connection and try again.',
            'error'
        );
    } finally {
        // Re-enable button
        submitBtn.disabled = false;
        submitBtn.textContent = 'Subscribe';
    }
});

function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function showMessage(text, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';

    // Auto-hide success messages after 10 seconds
    if (type === 'success') {
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 10000);
    }
}
