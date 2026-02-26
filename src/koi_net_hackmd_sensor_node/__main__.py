from rid_lib.ext import Bundle
from .core import HackMDSensorNode

if __name__ == "__main__":
    node = HackMDSensorNode()
    
    identity_bundle = Bundle.generate(
        rid=node.identity.rid,
        contents=node.identity.profile.model_dump()
    )
    node.cache.write(identity_bundle)

    node.run()