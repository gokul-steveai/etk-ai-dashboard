# A reusable master frame layout containing the shared styling, header, and footer structure
BASE_EMAIL_LAYOUT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{email_title}</title>
</head>
<body style="margin: 0; padding: 0; width: 100%; background-color: #f8fafc;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <tr>
            <td align="center" style="padding: 40px 16px;">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 520px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0; overflow: hidden;">
                    
                    <tr>
                        <td style="height: 6px; background: linear-gradient(90deg, {primary_color} 0%, #1d4ed8 100%);"></td>
                    </tr>

                    <tr>
                        <td style="padding: 40px 32px 32px 32px;">
                            <div style="font-size: 20px; font-weight: 700; color: #1e293b; margin-bottom: 32px;">
                                {app_name}
                            </div>

                            {email_body_content}

                        </td>
                    </tr>

                    <tr>
                        <td align="center" style="background-color: #f8fafc; padding: 24px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8;">
                            <p style="margin: 0;">&copy; {current_year} {company_name}. All rights reserved.</p>
                            <p style="margin: 4px 0 0 0; color: #cbd5e1; font-size: 11px;">Security Node • Automated Notification Layer</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

# Child layout context snippet focusing only on the specific registration variables
REGISTRATION_OTP_BODY = """
<h1 style="font-size: 24px; font-weight: 700; color: #0f172a; margin: 0 0 16px 0;">Verify your email address</h1>
<p style="font-size: 15px; line-height: 24px; color: #475569; margin: 0 0 32px 0;">
    Welcome, <strong>{username}</strong>! Thanks for joining us. To complete your account registration, please use the 6-digit verification code provided below:
</p>

<table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 32px;">
    <tr>
        <td align="center" style="background-color: #f1f5f9; border-radius: 8px; padding: 24px; border: 1px dashed #cbd5e1;">
            <div style="font-size: 36px; font-weight: 700; color: #1e3a8a; letter-spacing: 8px; font-family: monospace;">
                {otp_code}
            </div>
        </td>
    </tr>
</table>

<h4 style="color: #334155; margin: 0 0 8px 0; font-size: 14px;">Next Steps:</h4>
<ul style="padding-left: 20px; color: #475569; font-size: 14px; line-height: 20px; margin: 0 0 24px 0;">
    <li>Copy the 6-digit verification code listed above.</li>
    <li>Return to the application signup panel or active API documentation page.</li>
    <li>Submit the code within {expiry_minutes} minutes to complete registration.</li>
</ul>

<p style="font-size: 13px; line-height: 20px; color: #64748b; margin: 24px 0 0 0; border-top: 1px solid #f1f5f9; padding-top: 16px;">
    ⏱️ This security token is sensitive and will remain valid for exactly <strong>{expiry_minutes} minutes</strong>.
</p>
"""

PASSWORD_RESET_OTP_BODY = """
<h1 style="font-size: 24px; font-weight: 700; color: #0f172a; margin: 0 0 16px 0;">Reset your password</h1>
<p style="font-size: 15px; line-height: 24px; color: #475569; margin: 0 0 32px 0;">
    Hello, <strong>{username}</strong>. We received a request to reset the password for your account. Please use the 6-digit verification code provided below to proceed:
</p>

<table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 32px;">
    <tr>
        <td align="center" style="background-color: #ffffeb; border-radius: 8px; padding: 24px; border: 1px dashed #eab308;">
            <div style="font-size: 36px; font-weight: 700; color: #854d0e; letter-spacing: 8px; font-family: monospace;">
                {otp_code}
            </div>
        </td>
    </tr>
</table>

<h4 style="color: #334155; margin: 0 0 8px 0; font-size: 14px;">Important Details:</h4>
<ul style="padding-left: 20px; color: #475569; font-size: 14px; line-height: 20px; margin: 0 0 24px 0;">
    <li>This code is highly sensitive and is only valid for {expiry_minutes} minutes.</li>
    <li>Our team will never ask you for this token over chat, email, or telephone call.</li>
</ul>

<p style="font-size: 13px; line-height: 20px; color: #64748b; margin: 24px 0 0 0; border-top: 1px solid #f1f5f9; padding-top: 16px;">
    🔒 <strong>Didn't request this change?</strong> If you did not initiate this request, you can safely ignore this email. Your current password remains completely secure and active.
</p>
"""
