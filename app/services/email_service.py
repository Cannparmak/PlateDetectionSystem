"""Gmail SMTP üzerinden şifre sıfırlama maili gönderir."""

from __future__ import annotations

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings


def _build_html(reset_link: str, user_name: str, is_staff: bool) -> str:
    role_label = "Personel / Admin Hesabı" if is_staff else "Müşteri Hesabı"
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>CanPark — Şifre Sıfırlama</title>
</head>
<body style="margin:0;padding:0;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:48px 16px;">
    <tr>
      <td align="center">
        <table width="500" cellpadding="0" cellspacing="0" style="max-width:500px;width:100%;">

          <!-- Kart -->
          <tr>
            <td style="background:#1e1f26;border-radius:20px;overflow:hidden;
                       border:1px solid rgba(66,71,84,0.35);
                       box-shadow:0 0 40px rgba(0,0,0,0.5);">

              <!-- Üst şerit (adc6ff — mevcut accent rengi) -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#adc6ff;padding:28px 32px;">
                    <p style="margin:0;font-size:22px;font-weight:800;color:#002e6a;letter-spacing:-0.5px;">CanPark</p>
                    <p style="margin:4px 0 0;font-size:12px;color:#002e6a;opacity:0.7;">{role_label}</p>
                  </td>
                </tr>
              </table>

              <!-- İçerik -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:32px;">

                    <!-- Kilit ikonu kutusu -->
                    <table cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                      <tr>
                        <td style="background:rgba(173,198,255,0.1);border-radius:14px;
                                   width:52px;height:52px;text-align:center;vertical-align:middle;
                                   font-size:26px;border:1px solid rgba(173,198,255,0.15);">
                          🔐
                        </td>
                      </tr>
                    </table>

                    <p style="margin:0 0 6px;font-size:16px;font-weight:700;color:#e2e2eb;">
                      Merhaba, {user_name}
                    </p>
                    <p style="margin:0 0 28px;font-size:14px;color:#c2c6d6;line-height:1.7;">
                      Hesabınız için bir şifre sıfırlama talebi aldık.<br/>
                      Yeni şifrenizi oluşturmak için aşağıdaki butona tıklayın.
                    </p>

                    <!-- CTA butonu -->
                    <table cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
                      <tr>
                        <td style="border-radius:12px;background:#adc6ff;">
                          <a href="{reset_link}"
                             style="display:inline-block;padding:14px 32px;font-size:14px;
                                    font-weight:700;color:#002e6a;text-decoration:none;
                                    letter-spacing:0.1px;">
                            Şifremi Sıfırla &rarr;
                          </a>
                        </td>
                      </tr>
                    </table>

                    <!-- Uyarı kutusu -->
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);
                                   border-radius:10px;padding:14px 16px;">
                          <table cellpadding="0" cellspacing="0">
                            <tr>
                              <td style="font-size:16px;vertical-align:top;padding-right:10px;">⚠️</td>
                              <td style="font-size:12px;color:#c2c6d6;line-height:1.7;">
                                Bu bağlantı <strong style="color:#e2e2eb;">1 saat</strong> geçerlidir
                                ve yalnızca bir kez kullanılabilir.<br/>
                                Bu isteği siz yapmadıysanız e-postayı görmezden gelebilirsiniz.
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </table>

                  </td>
                </tr>
              </table>

              <!-- Footer -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="border-top:1px solid rgba(66,71,84,0.2);
                             padding:16px 32px;background:#191b22;">
                    <p style="margin:0;font-size:11px;color:#8c909f;text-align:center;">
                      CanPark Otopark Yönetim Sistemi &nbsp;·&nbsp; Bu e-posta otomatik gönderilmiştir.
                    </p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Alt yazı -->
          <tr>
            <td align="center" style="padding-top:20px;">
              <p style="margin:0;font-size:11px;color:#8c909f;">© 2025 CanPark. Tüm hakları saklıdır.</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _send_sync(to_email: str, reset_link: str, user_name: str, is_staff: bool) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "CanPark — Şifre Sıfırlama"
    msg["From"] = f"CanPark <{settings.MAIL_FROM}>"
    msg["To"] = to_email

    html = _build_html(reset_link, user_name, is_staff)
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(settings.MAIL_HOST, settings.MAIL_PORT, timeout=10) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        # Gmail App Password boşlukları kaldır
        password = settings.MAIL_PASSWORD.replace(" ", "")
        server.login(settings.MAIL_USERNAME, password)
        server.sendmail(settings.MAIL_FROM, to_email, msg.as_string())


async def send_password_reset_email(
    to_email: str,
    reset_link: str,
    user_name: str,
    is_staff: bool = True,
) -> None:
    """Şifre sıfırlama mailini thread pool'da gönderir (event loop'u bloklamaz)."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        _send_sync,
        to_email,
        reset_link,
        user_name,
        is_staff,
    )
