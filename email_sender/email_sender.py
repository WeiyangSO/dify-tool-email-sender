import smtplib
from email.mime.text import MIMEText
from email.header import Header
from typing import Dict, Any, List, Union

# Dify 工具开发依赖于其核心库，以下 import 为 Dify 内部结构示例。
# 在实际 Dify 环境中，这些基类会被正确加载。
from core.tools.tool.builtin_tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage, ToolInvokeMessageFlag


class EmailSenderTool(BuiltinTool):
    """
    一个用于通过 SMTP 发送邮件的 Dify 工具。
    """

    def _invoke(self, 
                user_id: str, 
                tool_parameters: Dict[str, Any], 
                ) -> Union[ToolInvokeMessage, List[ToolInvokeMessage]]:
        """
        Dify 在工作流中调用此方法来执行工具。
        """
        # 1. 从工具配置中获取所有已保存的 SMTP 账号信息
        # tool_configurations 是 Dify 平台注入的、用户在工具配置页保存的所有账号列表
        smtp_configs = self.runtime.credentials.get('smtp_accounts', [])
        if not smtp_configs:
            return self.create_text_message("错误：未在工具中配置任何发件人账号。请前往“工具”页面进行配置。")

        # 2. 确定使用哪个发件账号
        selected_account_name = tool_parameters.get('sender_account')
        
        target_config = None
        if selected_account_name:
            # 如果用户在节点中明确选择了一个账号
            target_config = next((c for c in smtp_configs if c.get('name') == selected_account_name), None)
            if not target_config:
                return self.create_text_message(f"错误：找不到名为 '{selected_account_name}' 的发件账号配置。")
        else:
            # 如果用户未选择，则寻找默认账号
            target_config = next((c for c in smtp_configs if c.get('is_default', False)), None)
            if not target_config:
                # 如果没有默认账号，则使用列表中的第一个作为后备
                target_config = smtp_configs[0]

        # 3. 解析邮件参数
        to_emails = [email.strip() for email in tool_parameters.get('to_emails', '').split(',') if email.strip()]
        if not to_emails:
            return self.create_text_message("错误：收件人邮箱(to_emails)不能为空。")

        subject = tool_parameters.get('subject', '来自 Dify 的邮件通知')
        body = tool_parameters.get('body', '')
        mail_type = tool_parameters.get('mail_type', 'html')
        encoding = tool_parameters.get('encoding', 'utf-8')
        cc_emails = [email.strip() for email in tool_parameters.get('cc_emails', '').split(',') if email.strip()]
        bcc_emails = [email.strip() for email in tool_parameters.get('bcc_emails', '').split(',') if email.strip()]

        # 4. 构造并发送邮件
        try:
            # 从选定的配置中获取 SMTP 详细信息
            smtp_server = target_config['server']
            smtp_port = int(target_config['port'])
            smtp_user = target_config['user']
            smtp_password = target_config['password'] # Dify 会自动处理解密
            sender_name = target_config['sender_name']
            
            # 构造邮件对象
            message = MIMEText(body, mail_type, encoding)
            message['From'] = Header(f"{sender_name} <{smtp_user}>", encoding)
            message['To'] = Header(", ".join(to_emails), encoding)
            if cc_emails:
                message['Cc'] = Header(", ".join(cc_emails), encoding)
            message['Subject'] = Header(subject, encoding)

            # 连接 SMTP 服务器并发送
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, to_emails + cc_emails + bcc_emails, message.as_string())
            
            # 5. 返回成功结果
            # 使用 Dify 的标准输出格式返回结果
            return self.create_json_message({
                "status": "success",
                "error_message": ""
            })

        except Exception as e:
            # 6. 返回详细的错误信息
            return self.create_json_message({
                "status": "error",
                "error_message": f"邮件发送失败: {str(e)}"
            })

    @classmethod
    def test_connection(cls, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        这个方法专门用于给 Dify 的“测试连接”按钮调用。
        它接收单个账号的凭证进行测试。
        """
        try:
            server = credentials.get('server')
            port = int(credentials.get('port'))
            user = credentials.get('user')
            password = credentials.get('password')

            with smtplib.SMTP_SSL(server, port, timeout=10) as smtp_server:
                smtp_server.login(user, password)
            
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
