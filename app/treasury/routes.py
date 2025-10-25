"""Treasury management API endpoints."""
from __future__ import annotations

from typing import Set

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

ALLOWED_ROLES = {"CFO", "CLO"}
ROLES_HEADER = "X-Org-Roles"

router = APIRouter(prefix="/api/v1/treasury", tags=["treasury"])


class WhitelistWalletRequest(BaseModel):
    """Payload to whitelist an outbound wallet destination."""

    chain: str = Field(..., min_length=1, description="Blockchain identifier, e.g. ETH or TON")
    address: str = Field(..., min_length=1, description="Wallet address that should be allowed for payouts")


class WhitelistWalletResponse(BaseModel):
    """Response indicating successful whitelist."""

    status: str = "whitelisted"
    chain: str
    address: str


def require_c_suite_role(
    x_org_roles: str | None = Header(default=None, alias=ROLES_HEADER)
) -> Set[str]:
    """Ensure the caller has at least one authorized leadership role."""

    if not x_org_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="role_header_required",
        )

    provided_roles = {role.strip().upper() for role in x_org_roles.split(",") if role.strip()}
    if not provided_roles & ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_role",
        )
    return provided_roles


@router.post("/whitelist_wallet", response_model=WhitelistWalletResponse)
def whitelist_wallet(
    payload: WhitelistWalletRequest,
    request: Request,
    _: Set[str] = Depends(require_c_suite_role),
) -> WhitelistWalletResponse:
    """Whitelist a wallet address for a specific blockchain."""

    chain = payload.chain.upper()
    address = payload.address.strip()

    whitelist = request.app.state.treasury_whitelist
    chain_whitelist = whitelist.setdefault(chain, set())
    chain_whitelist.add(address)

    return WhitelistWalletResponse(chain=chain, address=address)
