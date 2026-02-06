"""
이메일 발송 유틸리티
SMTP를 사용하여 견적서, 계약서 등을 이메일로 발송
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formataddr
from typing import Optional, Dict
import os


class EmailSender:
    """이메일 발송 클래스"""

    def __init__(self, host: str, port: int, email: str, password: str):
        self.host = host
        self.port = port
        self.email = email
        self.password = password

    def send_email(self, to_email: str, subject: str, body: str,
                   html_body: str = None, attachments: list = None,
                   from_name: str = None) -> Dict:
        """
        이메일 발송

        Args:
            to_email: 수신자 이메일
            subject: 제목
            body: 본문 (텍스트)
            html_body: 본문 (HTML, 선택)
            attachments: 첨부파일 리스트 [{'filename': ..., 'data': ...}]
            from_name: 발신자 이름

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 이메일 메시지 생성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((from_name, self.email)) if from_name else self.email
            msg['To'] = to_email

            # 텍스트 본문
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)

            # HTML 본문
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)

            # 첨부파일
            if attachments:
                for attachment in attachments:
                    part = MIMEApplication(attachment['data'])
                    part.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=attachment['filename']
                    )
                    msg.attach(part)

            # SMTP 연결 및 발송
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()  # TLS 보안 연결
                server.login(self.email, self.password)
                server.send_message(msg)

            return {'success': True, 'message': '이메일이 발송되었습니다.'}

        except smtplib.SMTPAuthenticationError:
            return {'success': False, 'message': 'SMTP 인증 실패. 이메일과 비밀번호를 확인하세요.'}
        except smtplib.SMTPException as e:
            return {'success': False, 'message': f'SMTP 오류: {str(e)}'}
        except Exception as e:
            return {'success': False, 'message': f'이메일 발송 오류: {str(e)}'}

    def send_quotation(self, to_email: str, client_name: str,
                      quotation_number: str, quotation_url: str,
                      pdf_data: bytes = None, company_name: str = None) -> Dict:
        """
        견적서 이메일 발송

        Args:
            to_email: 수신자 이메일
            client_name: 고객명
            quotation_number: 견적번호
            quotation_url: 견적서 확인 URL
            pdf_data: PDF 첨부파일 (선택)
            company_name: 회사명
        """
        subject = f"[견적서] {quotation_number} - {client_name}님"

        # 이메일 본문
        text_body = f"""{client_name}님 안녕하세요,

요청하신 프로젝트에 대한 견적서를 보내드립니다.

견적서 번호: {quotation_number}
견적서 확인 링크: {quotation_url}

첨부파일로 PDF 견적서도 함께 보내드립니다. 내용을 검토해 주시고,
궁금한 점이 있으시면 언제든지 연락 주시기 바랍니다.

감사합니다.

{company_name or ''}
"""

        # HTML 본문
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; padding: 30px; border-radius: 12px 12px 0 0; }}
        .content {{ background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 8px; margin: 20px 0; }}
        .button:hover {{ background: #1d4ed8; }}
        .footer {{ background: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #64748b; border-radius: 0 0 12px 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">견적서 도착</h1>
        </div>
        <div class="content">
            <p>안녕하세요, <strong>{client_name}</strong>님!</p>
            <p>요청하신 프로젝트에 대한 견적서가 도착했습니다.</p>

            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>견적서 번호:</strong> {quotation_number}</p>
            </div>

            <a href="{quotation_url}" class="button">견적서 확인하기</a>

            <p>첨부파일로 PDF 견적서도 함께 보내드립니다. 내용을 검토해 주시고,<br>
            궁금한 점이 있으시면 언제든지 연락 주시기 바랍니다.</p>
        </div>
        <div class="footer">
            <p>이 이메일은 발신 전용입니다. 문의사항은 담당자에게 직접 연락 바랍니다.</p>
            <p>&copy; 2025 {company_name or 'Agency'}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

        # 첨부파일
        attachments = []
        if pdf_data:
            attachments.append({
                'filename': f'견적서_{quotation_number}.pdf',
                'data': pdf_data
            })

        return self.send_email(
            to_email=to_email,
            subject=subject,
            body=text_body,
            html_body=html_body,
            attachments=attachments,
            from_name=company_name
        )

    @staticmethod
    def create_from_settings(settings: Dict) -> Optional['EmailSender']:
        """설정 딕셔너리로부터 EmailSender 인스턴스 생성"""
        host = settings.get('smtp_host')
        port = int(settings.get('smtp_port', 587))
        email = settings.get('smtp_email')
        password = settings.get('smtp_password')

        if not all([host, port, email, password]):
            return None

        return EmailSender(host, port, email, password)


def send_payment_reminder(to_email: str, client_name: str,
                         project_name: str, due_amount: int,
                         due_date: str, company_name: str = None) -> Dict:
    """
    입금 요청 알림 이메일 발송

    Args:
        to_email: 수신자 이메일
        client_name: 고객명
        project_name: 프로젝트명
        due_amount: 입금 예정 금액
        due_date: 입금 예정일
        company_name: 회사명
    """
    subject = f"[입금 요청] {project_name} - {due_date} 기한"

    text_body = f"""{client_name}님 안녕하세요,

진행 중인 프로젝트의 입금을 안내드립니다.

프로젝트명: {project_name}
입금 금액: {due_amount:,}원
입금 기한: {due_date}

지정된 기한 내에 입금 부탁드립니다.
입금 확인 후 프로젝트를 지속 진행하겠습니다.

감사합니다.

{company_name or ''}
"""

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .alert {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .info-box {{ background: #f1f5f9; padding: 20px; border-radius: 8px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>💳 입금 요청 알림</h2>
        <p>안녕하세요, <strong>{client_name}</strong>님!</p>

        <div class="alert">
            <strong>⚠️ 입금 기한이 임박했습니다.</strong>
        </div>

        <div class="info-box">
            <p><strong>프로젝트명:</strong> {project_name}</p>
            <p><strong>입금 금액:</strong> {due_amount:,}원</p>
            <p><strong>입금 기한:</strong> {due_date}</p>
        </div>

        <p>지정된 기한 내에 입금 부탁드립니다.<br>
        입금 확인 후 프로젝트를 지속 진행하겠습니다.</p>

        <p>감사합니다.</p>
    </div>
</body>
</html>
"""

    # 설정에서 SMTP 정보 가져오기 (여기서는 DB 직접 접근)
    from database import SettingsDB
    settings_db = SettingsDB()
    smtp_settings = settings_db.get_all_settings()

    sender = EmailSender.create_from_settings(smtp_settings)
    if not sender:
        return {'success': False, 'message': 'SMTP 설정이 되어 있지 않습니다.'}

    return sender.send_email(
        to_email=to_email,
        subject=subject,
        body=text_body,
        html_body=html_body,
        from_name=company_name
    )
