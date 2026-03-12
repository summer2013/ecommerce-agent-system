# agents/shared/email_client.py
import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from dotenv import load_dotenv
import datetime

load_dotenv()

EMAIL_ADDRESS    = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD   = os.getenv("EMAIL_PASSWORD")
IMAP_SERVER      = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
SMTP_SERVER      = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT        = int(os.getenv("EMAIL_SMTP_PORT", "587"))


def decode_str(s) -> str:
    """解码邮件头部（标题、发件人等可能是编码格式）"""
    if s is None:
        return ""
    parts = decode_header(s)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="ignore"))
        else:
            result.append(part)
    return "".join(result)


def fetch_unread_emails(keyword: str = None) -> list[dict]:
    """
    获取收件箱未读邮件
    keyword: 可选，只返回标题包含该关键词的邮件
    返回: 邮件字典列表
    """
    result = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mail.select("inbox")

        # 搜索未读邮件
        _, message_ids = mail.search(None, "UNSEEN")

        for msg_id in message_ids[0].split():
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            subject = decode_str(msg["Subject"])
            sender  = decode_str(msg["From"])

            # 如果指定了关键词，过滤不匹配的邮件
            if keyword and keyword not in subject:
                continue

            # 提取正文和附件
            body = ""
            attachments = []

            for part in msg.walk():
                content_type = part.get_content_type()
                disposition  = str(part.get("Content-Disposition"))

                if content_type == "text/plain" and "attachment" not in disposition:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                elif "attachment" in disposition:
                    filename = decode_str(part.get_filename())
                    if filename:
                        attachments.append({
                            "filename": filename,
                            "data": part.get_payload(decode=True)
                        })

            result.append({
                "msg_id": msg_id,
                "subject": subject,
                "sender": sender,
                "body": body,
                "attachments": attachments,
                "received_at": datetime.datetime.now(),
            })

        mail.logout()
    except Exception as e:
        print(f"⚠ 邮件读取失败：{e}")

    return result


def send_email(to: str, subject: str, body: str) -> bool:
    """发送邮件，返回是否成功"""
    try:
        msg = MIMEMultipart()
        msg["From"]    = EMAIL_ADDRESS
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"⚠ 邮件发送失败：{e}")
        return False


# 直接运行验证连接
if __name__ == "__main__":
    print("正在连接邮箱...")
    emails = fetch_unread_emails()
    print(f"✅ 连接成功，当前有 {len(emails)} 封未读邮件")