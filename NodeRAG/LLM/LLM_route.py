import asyncio
import time
from .LLM_base import I,O,Dict
from .LLM import *

from ..logging.error import (
    cache_error,
    cache_error_async
)



def LLM_route(config : ModelConfig) -> LLM:
    
    '''Route the request to the appropriate LLM service provider'''
        


    service_provider = config.get("service_provider")
    model_name = config.get("model_name")
    embedding_model_name = config.get("embedding_model_name",None)
    api_keys = config.get("api_keys",None)
        
    match service_provider:
        case "openai":
            return OPENAI(model_name, api_keys, config)
        case "openai_embedding":
            return OpenAI_Embedding(embedding_model_name, api_keys, config)
        case "gemini":
            return Gemini(model_name, api_keys, config)
        case "gemini_embedding":
            return Gemini_Embedding(embedding_model_name, api_keys, config)
        case _:
            raise ValueError("Service provider not supported")
   
            

class API_client():
    
    def __init__(self, 
                 config : ModelConfig) -> None:
        
        self.llm = LLM_route(config)
        # rate_limit is interpreted as requests per minute for time-based limiting
        requests_per_minute = config.get("rate_limit", 10)
        # Semaphore limits concurrent requests (set to 1 for strict rate limiting)
        self.semaphore = asyncio.Semaphore(1)
        # Calculate minimum delay between requests: 60 seconds / requests_per_minute
        # For 10 requests/minute, this is 6 seconds between requests
        self.min_delay = 60.0 / requests_per_minute if requests_per_minute > 0 else 6.0
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()


            
    @cache_error_async
    async def __call__(self, input: I, *,cache_path:str|None=None,meta_data:Dict|None=None) -> O:
        
        async with self.semaphore:
            # Time-based rate limiting
            async with self._lock:
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.min_delay:
                    await asyncio.sleep(self.min_delay - time_since_last)
                self.last_request_time = time.time()
            
            response = await self.llm.predict_async(input)

            
        return response
    
    @cache_error
    def request(self, input:I, *,cache_path:str|None=None,meta_data:Dict|None=None) -> O:
        

        response = self.llm.predict(input)
        
        
        return response
    
    def stream_chat(self,input:I):
        yield from self.llm.stream_chat(input)
    
    
