import asyncio
import httpx


class HackMDClient:
    api_base_url = "https://api.hackmd.io/v1"

    def __init__(self, api_token: str):
        self.api_token = api_token

    def request(self, path, method="GET"):
        resp = httpx.request(
            method, self.api_base_url+path,
            headers={
                "Authorization": "Bearer " + self.api_token
            }
        )

        if resp.status_code == 200:
            return resp.json()
        
        else:
            print(resp.status_code, resp.text)
            return

    async def async_request(self, path, method="GET"):
        timeout = 60
        
        while True: 
            async with httpx.AsyncClient() as client:
                
                resp = await client.request(
                    method, self.api_base_url + path,
                    headers={
                        "Authorization": "Bearer " + self.api_token
                    }
                )
            

            if resp.status_code == 200:
                return resp.json()

            elif resp.status_code == 429:
                print(resp.status_code, resp.text, f"retrying in {timeout} seconds")
                await asyncio.sleep(timeout)
                timeout *= 2
            else:
                print(resp.status_code, resp.text)
                return