from apryse_sdk.PDFNetPython import PDFNet
from src.utils.metaclasses import DynamicSingleton


class ApryseSession(metaclass=DynamicSingleton):
    def __init__(self, api_key: str):
        PDFNet.Initialize(api_key)
        PDFNet.SetDefaultDiskCachingEnabled(False)
