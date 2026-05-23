import { Resend } from 'resend';

const resendApiKey = process.env.RESEND_API_KEY;
const fromEmail = process.env.FROM_EMAIL || 'CourtPulse <onboarding@resend.dev>';

const resend = resendApiKey ? new Resend(resendApiKey) : null;

/**
 * Send magic link email. Uses Resend when RESEND_API_KEY is set.
 * In dev without the key, the caller should log the link instead.
 */
export async function sendMagicLinkEmail(to: string, verifyUrl: string): Promise<{ ok: boolean; error?: string }> {
  if (!resend) {
    return { ok: false, error: 'RESEND_API_KEY not configured' };
  }

  const { data, error } = await resend.emails.send({
    from: fromEmail,
    to: [to],
    subject: 'Sign in to CourtPulse',
    html: `
      <p>Click the link below to sign in to CourtPulse. This link expires in 15 minutes.</p>
      <p><a href="${verifyUrl}">${verifyUrl}</a></p>
      <p>If you didn't request this, you can ignore this email.</p>
    `
  });

  if (error) {
    return { ok: false, error: error.message };
  }
  return { ok: true };
}

const ADMIN_EMAIL = 'matthewmctighe1@gmail.com';

export async function sendDeletionRequestEmail(params: {
  courtId: number;
  courtName: string;
  requesterEmail: string;
  reason: string | null;
}): Promise<void> {
  const { courtId, courtName, requesterEmail, reason } = params;

  if (!resend) {
    throw new Error('Email service not configured — cannot send deletion request');
  }

  await resend.emails.send({
    from: fromEmail,
    to: [ADMIN_EMAIL],
    subject: `Court deletion request: ${courtName}`,
    html: `
      <p><strong>${requesterEmail}</strong> has requested that the following court be deleted:</p>
      <ul>
        <li><strong>Court:</strong> ${courtName} (ID: ${courtId})</li>
        <li><strong>Reason:</strong> ${reason || 'No reason provided'}</li>
        <li><strong>Requested by:</strong> ${requesterEmail}</li>
      </ul>
      <p>Log in to CourtPulse as admin to delete this court.</p>
    `,
  });
}
