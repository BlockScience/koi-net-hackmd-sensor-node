import uvicorn
from .config import HOST, PORT

uvicorn.run("hackmd_sensor_node.server:app", host=HOST, port=PORT)