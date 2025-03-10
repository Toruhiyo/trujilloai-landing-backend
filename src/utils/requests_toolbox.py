from fastapi import Request


def get_request_relevant_data(request: Request):
    client = request.client
    client_host = client.host if client else None
    client_port = client.port if client else None
    user_agent = request.headers.get("User-Agent")
    return {
        "client_host": client_host,
        "client_port": client_port,
        "user_agent": user_agent,
    }
