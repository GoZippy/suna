'use server';

import { redirect } from 'next/navigation';

// Local authentication - no Supabase dependencies
const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:18080';

async function sendWelcomeEmail(email: string, name?: string) {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    const adminApiKey = process.env.KORTIX_ADMIN_API_KEY;
    
    if (!adminApiKey) {
      console.error('KORTIX_ADMIN_API_KEY not configured');
      return;
    }
    
    const response = await fetch(`${backendUrl}/api/send-welcome-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Api-Key': adminApiKey,
      },
      body: JSON.stringify({
        email,
        name,
      }),
    });

    if (response.ok) {
    } else {
      const errorData = await response.json().catch(() => ({}));
      console.error(`Failed to queue welcome email for ${email}:`, errorData);
    }
  } catch (error) {
    console.error('Error sending welcome email:', error);
  }
}

export async function signIn(prevState: any, formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  const returnUrl = formData.get('returnUrl') as string | undefined;

  if (!email || !email.includes('@')) {
    return { message: 'Please enter a valid email address' };
  }

  if (!password || password.length < 6) {
    return { message: 'Password must be at least 6 characters' };
  }

  try {
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return { message: errorData.detail || 'Could not authenticate user' };
    }

    // Login successful - the client-side auth provider will handle the session
    return { success: true, redirectTo: returnUrl || '/dashboard' };
  } catch (error) {
    console.error('Sign in error:', error);
    return { message: 'Network error - please try again' };
  }
}

export async function signUp(prevState: any, formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  const confirmPassword = formData.get('confirmPassword') as string;
  const returnUrl = formData.get('returnUrl') as string | undefined;

  if (!email || !email.includes('@')) {
    return { message: 'Please enter a valid email address' };
  }

  if (!password || password.length < 8) {
    return { message: 'Password must be at least 8 characters' };
  }

  if (password !== confirmPassword) {
    return { message: 'Passwords do not match' };
  }

  try {
    const response = await fetch(`${API_URL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        role: 'user',
        tier: 'free'
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return { message: errorData.detail || 'Could not create account' };
    }

    const userName = email.split('@')[0].replace(/[._-]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

    // Send welcome email
    sendWelcomeEmail(email, userName);

    // Registration successful - the client-side auth provider will handle the session
    return { success: true, redirectTo: returnUrl || '/dashboard' };
  } catch (error) {
    console.error('Sign up error:', error);
    return { message: 'Network error - please try again' };
  }
}

export async function forgotPassword(prevState: any, formData: FormData) {
  const email = formData.get('email') as string;

  if (!email || !email.includes('@')) {
    return { message: 'Please enter a valid email address' };
  }

  try {
    // For self-hosted, we'll show a message that password reset needs to be handled manually
    // In a production self-hosted setup, you would implement your own password reset mechanism
    return {
      success: false,
      message: 'Password reset not implemented for self-hosted. Please contact your administrator.',
    };
  } catch (error) {
    console.error('Forgot password error:', error);
    return { message: 'Network error - please try again' };
  }
}

export async function resetPassword(prevState: any, formData: FormData) {
  const password = formData.get('password') as string;
  const confirmPassword = formData.get('confirmPassword') as string;

  if (!password || password.length < 8) {
    return { message: 'Password must be at least 8 characters' };
  }

  if (password !== confirmPassword) {
    return { message: 'Passwords do not match' };
  }

  try {
    // For self-hosted, password reset would need to be implemented via admin API
    return {
      success: false,
      message: 'Password reset not implemented for self-hosted. Please contact your administrator.',
    };
  } catch (error) {
    console.error('Reset password error:', error);
    return { message: 'Network error - please try again' };
  }
}

export async function signOut() {
  try {
    // For local auth, we'll just redirect to home and let client handle session cleanup
    return redirect('/');
  } catch (error) {
    console.error('Sign out error:', error);
    return redirect('/');
  }
}
