"""
Provider seçim mantığı burada izole edilir. Yeni bir sağlayıcı eklemek
için sadece aşağıdaki if/elif zincirine bir satır eklemek yeterlidir.
"""
from app.config.settings import Settings
from app.llm.base import BaseLLM
from app.llm.anthropic_llm import AnthropicLLM
from app.llm.mistral_llm import MistralLLM


# Eğer sisteminde bir MockLLM varsa onu da import edebilirsin, örneğin:
# from app.llm.mock_llm import MockLLM

def get_llm(settings: Settings) -> BaseLLM:
    """
    Çevresel değişkenlere (settings) bakarak doğru LLM sağlayıcısını üretir (Factory Pattern).
    """
    provider = getattr(settings, "LLM_PROVIDER", "mock").lower()

    if provider == "mistral":
        return MistralLLM(
            api_key=settings.MISTRAL_API_KEY,
            model=getattr(settings, "MISTRAL_MODEL", "mistral-large-latest")
        )
    elif provider == "anthropic":
        return AnthropicLLM(
            api_key=settings.ANTHROPIC_API_KEY,

            model=getattr(settings, "ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        )
    # Eğer yeni bir llm eklenirse buraya ekleme yapılacak

    else:
        # Mock veya varsayılan durum
        # return MockLLM()
        raise ValueError(f"Desteklenmeyen LLM sağlayıcısı: {provider}")
