from protocols.no_protocol import NoProtocol
from protocols.credit_bureau import CreditBureauProtocol
from protocols.peer_ratings import PeerRatingsProtocol
from protocols.anonymity import AnonymityProtocol
from protocols.mandatory_audit import MandatoryAuditProtocol
from protocols.custom import CustomProtocol

PROTOCOL_META = {
    "no_protocol":      {"name": "No Protocol (Baseline)", "description": "Pure free market. Buyers don't remember seller identities. No oversight."},
    "credit_bureau":    {"name": "Centralized Reputation", "description": "Central authority tracks quality accuracy and computes seller reliability scores."},
    "peer_ratings":     {"name": "Peer Ratings", "description": "Buyers rate sellers 1-5 stars after quality revealed. All ratings public."},
    "anonymity":        {"name": "Full Anonymity", "description": "Agents cannot identify each other. No messaging. No forum."},
    "mandatory_audit":  {"name": "Mandatory Audit", "description": "25% of transactions randomly audited. Misrepresentation triggers 25% penalty."},
    "custom":           {"name": "Custom Protocol", "description": "User-defined protocol."},
}


def create_protocol(config: dict):
    system = config.get("protocol", {}).get("system", "no_protocol")
    description = config.get("protocol", {}).get("description", "")
    if system == "no_protocol":
        return NoProtocol()
    elif system == "credit_bureau":
        return CreditBureauProtocol()
    elif system == "peer_ratings":
        return PeerRatingsProtocol()
    elif system == "anonymity":
        return AnonymityProtocol()
    elif system == "mandatory_audit":
        return MandatoryAuditProtocol()
    elif system == "custom":
        return CustomProtocol(description=description)
    return NoProtocol()
