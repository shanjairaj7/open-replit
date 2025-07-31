"""
Simple proxy server to forward requests to Vite dev server
"""
import asyncio
import aiohttp
from aiohttp import web
import logging

logger = logging.getLogger(__name__)

async def proxy_handler(request):
    """Proxy all requests to the Vite dev server"""
    target_url = f"http://localhost:3000{request.path_qs}"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Forward the request
            async with session.request(
                method=request.method,
                url=target_url,
                headers={k: v for k, v in request.headers.items() if k.lower() not in ['host', 'content-length']},
                data=await request.read(),
                allow_redirects=False
            ) as response:
                # Create proxy response
                body = await response.read()
                proxy_response = web.Response(
                    body=body,
                    status=response.status,
                    headers={k: v for k, v in response.headers.items() if k.lower() not in ['content-encoding', 'content-length', 'transfer-encoding']}
                )
                return proxy_response
                
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return web.Response(text=f"Proxy error: {str(e)}", status=500)

async def health_check(request):
    """Health check endpoint"""
    return web.json_response({"status": "healthy", "service": "vite-proxy"})

app = web.Application()
app.router.add_route('*', '/health', health_check)
app.router.add_route('*', '/{path:.*}', proxy_handler)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    web.run_app(app, host='0.0.0.0', port=port)