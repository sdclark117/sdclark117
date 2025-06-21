# Stripe Integration Setup Guide

To handle subscriptions and payments, the application uses Stripe. You will need to create a Stripe account, add your products and prices, and configure webhook endpoints.

Follow these steps to get everything set up:

## Step 1: Create a Stripe Account

1.  If you don't already have one, go to the [Stripe website](https://dashboard.stripe.com/register) and create an account.
2.  Once your account is created, you can access your **Test Mode** dashboard. This is a sandbox environment where you can build and test your integration without using real money.

## Step 2: Find Your API Keys

1.  In your Stripe Dashboard, go to the **"Developers" > "API keys"** section.
2.  You will find your **Publishable key** and **Secret key**. These are your test keys.
3.  You will need to add these as environment variables in your Render project:
    *   **Key**: `STRIPE_PUBLISHABLE_KEY`, **Value**: Your Publishable key (starts with `pk_test_...`)
    *   **Key**: `STRIPE_SECRET_KEY`, **Value**: Your Secret key (starts with `sk_test_...`)

## Step 3: Create Your Products and Prices

You need to create a product for each of your subscription plans in the Stripe dashboard.

1.  Go to the **"Products"** tab in your Stripe Dashboard.
2.  Click **"+ Add product"** to create your three plans:

    *   **Plan 1: BASIC**
        *   **Name**: BASIC
        *   **Description**: "50 searches per month"
        *   Under "Pricing", set the price to **$19.99** and select **"Recurring"**. The billing period should be **"Monthly"**.

    *   **Plan 2: PREMIUM**
        *   **Name**: PREMIUM
        *   **Description**: "100 searches per month"
        *   Under "Pricing", set the price to **$49.99** and select **"Recurring"**. The billing period should be **"Monthly"**.

    *   **Plan 3: PLATINUM**
        *   **Name**: PLATINUM
        *   **Description**: "Unlimited searches per month"
        *   Under "Pricing", set the price to **$99.99** and select **"Recurring"**. The billing period should be **"Monthly"**.

3.  After creating each product and its price, click on the price to view its details. You will need the **Price ID** (it looks like `price_...`).
4.  Add these Price IDs as environment variables in Render:
    *   **Key**: `STRIPE_BASIC_PLAN_PRICE_ID`, **Value**: Your Price ID for the BASIC plan.
    *   **Key**: `STRIPE_PREMIUM_PLAN_PRICE_ID`, **Value**: Your Price ID for the PREMIUM plan.
    *   **Key**: `STRIPE_PLATINUM_PLAN_PRICE_ID`, **Value**: Your Price ID for the PLATINUM plan.

## Step 4: Set Up a Webhook Endpoint

Stripe uses webhooks to send real-time notifications to your application about events like successful payments, failed payments, or subscription cancellations.

1.  In your Stripe Dashboard, go to **"Developers" > "Webhooks"**.
2.  Click **"+ Add endpoint"**.
3.  For the **"Endpoint URL"**, enter your application's webhook URL. This will be your website's URL followed by `/stripe-webhook`. For example: `https://your-app-name.onrender.com/stripe-webhook`
4.  For the **"Version"**, select the latest API version.
5.  Click **"Select events"** and choose the following events to listen to:
    *   `checkout.session.completed`
    *   `customer.subscription.updated`
    *   `customer.subscription.deleted`
6.  Click **"Add endpoint"**.
7.  After creating the endpoint, Stripe will show you a **Webhook signing secret**. This is a special key used to verify that the webhook requests are coming from Stripe.
8.  Add this as an environment variable in Render:
    *   **Key**: `STRIPE_WEBHOOK_SECRET`, **Value**: Your Webhook signing secret (starts with `whsec_...`)

Once you've completed these steps and set all the environment variables in Render, your application will be fully configured to handle subscriptions and payments. 