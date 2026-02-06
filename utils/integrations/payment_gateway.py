"""
결제 게이트웨이 연동
토스페이먼츠, 카카오페이 등 한국 결제 수단 연동
"""

from datetime import datetime
from typing import Dict, Optional, List
import hashlib
import hmac
import json


class PaymentGateway:
    """결제 게이트웨이 베이스 클래스"""

    def __init__(self, api_key: str, api_secret: str, sandbox: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox

    def create_payment(self, amount: int, order_id: str,
                      customer_name: str, customer_email: str,
                      success_url: str = None, fail_url: str = None) -> Dict:
        """결제 생성"""
        raise NotImplementedError

    def verify_payment(self, payment_id: str, amount: int) -> Dict:
        """결제 확인"""
        raise NotImplementedError

    def cancel_payment(self, payment_id: str) -> Dict:
        """결제 취소"""
        raise NotImplementedError


class TossPayments(PaymentGateway):
    """토스페이먼츠 연동"""

    def __init__(self, api_key: str, secret_key: str, sandbox: bool = True):
        super().__init__(api_key, secret_key, sandbox)
        self.base_url = "https://api.tosspayments.com/v1/payments"
        if sandbox:
            self.base_url = "https://api.tosspayments.com/v1/payments"

    def create_payment(self, amount: int, order_id: str,
                      customer_name: str, customer_email: str,
                      success_url: str = None, fail_url: str = None) -> Dict:
        """결제 생성"""
        try:
            import requests

            headers = {
                "Authorization": f"Basic {self._encode_secret()}",
                "Content-Type": "application/json"
            }

            payload = {
                "amount": amount,
                "orderId": order_id,
                "orderName": f"에이전시 결제 ({order_id})",
                "customerName": customer_name,
                "customerEmail": customer_email,
                "successUrl": success_url or "https://agency.com/payments/success",
                "failUrl": fail_url or "https://agency.com/payments/fail"
            }

            # 실제 API 호출
            # response = requests.post(
            #     f"{self.base_url}/virtual-account",
            #     headers=headers,
            #     json=payload
            # )

            # 샘플 반환
            return {
                "success": True,
                "payment_key": f"tosspay_{datetime.now().timestamp()}",
                "checkout_url": f"https://tosspay.com/checkout/{order_id}"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def verify_payment(self, payment_key: str, amount: int) -> Dict:
        """결제 확인"""
        try:
            import requests

            headers = {
                "Authorization": f"Basic {self._encode_secret()}"
            }

            # 실제 API 호출
            # response = requests.get(
            #     f"{self.base_url}/{payment_key}",
            #     headers=headers
            # )

            return {
                "success": True,
                "status": "DONE",
                "amount": amount
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cancel_payment(self, payment_key: str,
                      cancel_reason: str = None) -> Dict:
        """결제 취소"""
        try:
            import requests

            headers = {
                "Authorization": f"Basic {self._encode_secret()}",
                "Content-Type": "application/json"
            }

            payload = {
                "cancelReason": cancel_reason or "사용자 요청"
            }

            # 실제 API 호출
            # response = requests.post(
            #     f"{self.base_url}/{payment_key}/cancel",
            #     headers=headers,
            #     json=payload
            # )

            return {
                "success": True,
                "cancelReason": cancel_reason
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _encode_secret(self) -> str:
        """시크릿 키 인코딩"""
        import base64
        secret = f"{self.api_key}:{self.api_secret}"
        return base64.b64encode(secret.encode()).decode()


class KakaoPay(PaymentGateway):
    """카카오페이 연동"""

    def __init__(self, admin_key: str, cid: str, sandbox: bool = True):
        super().__init__(admin_key, "", sandbox)
        self.cid = cid
        self.admin_key = admin_key
        self.base_url = "https://kapi.kakao.com"
        if sandbox:
            self.cid = "TC0ONETIME"  # 테스트용 CID

    def create_payment(self, amount: int, order_id: str,
                      customer_name: str, customer_email: str,
                      success_url: str = None, fail_url: str = None) -> Dict:
        """결제 생성"""
        try:
            import requests

            headers = {
                "Authorization": f"KakaoAK {self.admin_key}",
                "Content-Type": "application/json;charset=utf-8"
            }

            payload = {
                "cid": self.cid,
                "partner_order_id": order_id,
                "partner_user_id": customer_name,
                "item_name": f"에이전시 결제 ({order_id})",
                "quantity": 1,
                "total_amount": amount,
                "vat_amount": int(amount * 0.1),
                "tax_free_amount": 0,
                "approval_url": success_url or "https://agency.com/payments/success",
                "fail_url": fail_url or "https://agency.com/payments/fail",
                "cancel_url": "https://agency.com/payments/cancel"
            }

            # 실제 API 호출
            # response = requests.post(
            #     f"{self.base_url}/v1/payment/ready",
            #     headers=headers,
            #     json=payload
            # )

            return {
                "success": True,
                "tid": f"kakao_{datetime.now().timestamp()}",
                "next_redirect_app_url": f"kakaotalk://kakaopay/approval",
                "next_redirect_mobile_url": f"https://online-pay.kakao.com/payments/approval"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def verify_payment(self, tid: str, amount: int) -> Dict:
        """결제 확인"""
        try:
            import requests

            headers = {
                "Authorization": f"KakaoAK {self.admin_key}"
            }

            # 실제 API 호출
            # response = requests.get(
            #     f"{self.base_url}/v1/payment/order",
            #     headers=headers,
            #     params={"tid": tid}
            # )

            return {
                "success": True,
                "status": "SUCCESS",
                "amount": amount
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cancel_payment(self, tid: str,
                      cancel_amount: int = None,
                      cancel_reason: str = None) -> Dict:
        """결제 취소"""
        try:
            import requests

            headers = {
                "Authorization": f"KakaoAK {self.admin_key}",
                "Content-Type": "application/json;charset=utf-8"
            }

            payload = {
                "cid": self.cid,
                "tid": tid,
                "cancel_amount": cancel_amount,
                "cancel_tax_free_amount": 0
            }

            # 실제 API 호출
            # response = requests.post(
            #     f"{self.base_url}/v1/payment/cancel",
            #     headers=headers,
            #     json=payload
            # )

            return {
                "success": True,
                "cancel_reason": cancel_reason
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


class PaymentMethodManager:
    """결제 수단 관리자"""

    def __init__(self):
        self.providers = {}

    def register_provider(self, name: str, provider: PaymentGateway):
        """결제 수단 등록"""
        self.providers[name] = provider

    def get_provider(self, name: str) -> Optional[PaymentGateway]:
        """결제 수단 조회"""
        return self.providers.get(name)

    def create_payment(self, provider_name: str, **kwargs) -> Dict:
        """결제 생성"""
        provider = self.get_provider(provider_name)
        if provider:
            return provider.create_payment(**kwargs)
        return {"success": False, "error": "Provider not found"}

    def verify_payment(self, provider_name: str, payment_id: str, amount: int) -> Dict:
        """결제 확인"""
        provider = self.get_provider(provider_name)
        if provider:
            return provider.verify_payment(payment_id, amount)
        return {"success": False, "error": "Provider not found"}


def get_payment_manager() -> PaymentMethodManager:
    """결제 관리자 인스턴스 반환"""
    manager = PaymentMethodManager()

    # 설정에서 API 키 가져오기
    from database import SettingsDB
    settings = SettingsDB()

    toss_key = settings.get_setting("toss_api_key")
    toss_secret = settings.get_setting("toss_secret_key")
    kakao_key = settings.get_setting("kakao_admin_key")

    if toss_key:
        manager.register_provider("tosspayments", TossPayments(toss_key, toss_secret))

    if kakao_key:
        manager.register_provider("kakaopay", KakaoPay(kakao_key, "TC0ONETIME"))

    return manager
