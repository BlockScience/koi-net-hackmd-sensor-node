import uvicorn
from .core import node

uvicorn.run(
    "hackmd_sensor_node.server:app", 
    host=node.config.server.host,
    port=node.config.server.port, 
)