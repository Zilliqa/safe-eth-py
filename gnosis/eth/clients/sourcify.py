from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from .. import EthereumNetwork
from ..utils import fast_is_checksum_address
from .contract_metadata import ContractMetadata


class Sourcify:
    """
    Get contract metadata from Sourcify. Matches can be full or partial:

      - Full: Both the source files as well as the meta data files were an exact match between the deployed bytecode
        and the published files.
      - Partial: Source code compiles to the same bytecode and thus the contract behaves in the same way,
        but the source code can be different: Variables can have misleading names,
        comments can be different and especially the NatSpec comments could have been modified.

    """

    def __init__(
        self,
        network: EthereumNetwork = EthereumNetwork.MAINNET,
        base_url: str = "https://repo.sourcify.dev/",
        request_timeout: int = 10,
    ):
        self.network = network
        self.base_url = base_url
        self.http_session = self._prepare_http_session()
        self.request_timeout = request_timeout

    def _prepare_http_session(self) -> requests.Session:
        """
        Prepare http session with custom pooling. See:
        https://urllib3.readthedocs.io/en/stable/advanced-usage.html
        https://2.python-requests.org/en/latest/api/#requests.adapters.HTTPAdapter
        https://web3py.readthedocs.io/en/stable/providers.html#httpprovider
        """
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=100,
            pool_block=False,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _get_abi_from_metadata(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        return metadata["output"]["abi"]

    def _get_name_from_metadata(self, metadata: Dict[str, Any]) -> Optional[str]:
        values = list(metadata["settings"].get("compilationTarget", {}).values())
        if values:
            return values[0]

    def _do_request(self, url: str) -> Optional[Dict[str, Any]]:
        response = self.http_session.get(url, timeout=self.request_timeout)
        if not response.ok:
            return None

        return response.json()

    def get_contract_metadata(
        self, contract_address: str
    ) -> Optional[ContractMetadata]:
        assert fast_is_checksum_address(
            contract_address
        ), "Expecting a checksummed address"

        for match_type in ("full_match", "partial_match"):
            url = urljoin(
                self.base_url,
                f"/contracts/{match_type}/{self.network.value}/{contract_address}/metadata.json",
            )
            metadata = self._do_request(url)
            if metadata:
                abi = self._get_abi_from_metadata(metadata)
                name = self._get_name_from_metadata(metadata)
                return ContractMetadata(name, abi, match_type == "partial_match")
        return None
