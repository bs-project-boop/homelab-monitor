import ssl

import httpx

from app.collectors.proxmox import payloads_to_snapshot, snapshot_to_resources
from app.collectors.proxmox_jobs import scheduled_jobs_to_resources
from app.services.collector import CollectionSourceResult


class ProxmoxApiSource:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        ca_cert: str,
        node_name: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.ca_cert = ca_cert
        self.node_name = node_name
        self.transport = transport

    async def fetch(self) -> CollectionSourceResult:
        headers = {"Authorization": f"PVEAPIToken={self.token}"}
        context = ssl.create_default_context(
            cafile=None if self.transport is not None else self.ca_cert
        )
        if hasattr(ssl, "VERIFY_X509_STRICT"):
            context.verify_flags &= ~ssl.VERIFY_X509_STRICT
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            verify=context,
            timeout=httpx.Timeout(10.0, connect=3.0),
            transport=self.transport,
        ) as client:
            node = await self._get(client, f"/api2/json/nodes/{self.node_name}/status")
            lxc = await self._get(client, f"/api2/json/nodes/{self.node_name}/lxc")
            qemu = await self._get(client, f"/api2/json/nodes/{self.node_name}/qemu")
            backups = await self._get(client, "/api2/json/cluster/backup")
            replications = await self._get(client, "/api2/json/cluster/replication")
        snapshot = payloads_to_snapshot(
            node_name=self.node_name, node_payload=node, lxc_payload=lxc, qemu_payload=qemu
        )
        node_id = f"proxmox:node:{self.node_name}"
        resources = snapshot_to_resources(snapshot)
        resources.extend(scheduled_jobs_to_resources(node_id=node_id, backups=backups, replications=replications))
        return CollectionSourceResult(source="proxmox", resources=resources)

    @staticmethod
    async def _get(client: httpx.AsyncClient, path: str) -> object:
        response = await client.get(path)
        if response.status_code >= 400:
            raise RuntimeError(f"proxmox_api_http_{response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise RuntimeError("proxmox_api_invalid_json") from exc
        if not isinstance(body, dict) or "data" not in body:
            raise RuntimeError("proxmox_api_invalid_envelope")
        return body["data"]
