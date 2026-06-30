"""VPC service-specific routes."""

import base64
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.aws_client import get_client
from backend.routes.common import EndpointInfo, get_endpoint_info

router = APIRouter()

@router.get("/vpcs")
def list_vpcs(ep: EndpointInfo = Depends(get_endpoint_info)) -> dict[str, Any]:
    """List all VPCs with their subnets."""
    try:
        client = get_client("ec2", **ep.client_kwargs())
        vpcs_response = client.describe_vpcs()

        vpcs = []
        for vpc in vpcs_response.get("Vpcs", []):
            vpc_id = vpc["VpcId"]

            # Get subnets for this VPC
            subnets_response = client.describe_subnets(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            )

            subnets = []
            for subnet in subnets_response.get("Subnets", []):
                subnets.append(
                    {
                        "subnetId": subnet["SubnetId"],
                        "cidrBlock": subnet["CidrBlock"],
                        "availabilityZone": subnet["AvailabilityZone"],
                        "availableIpAddressCount": subnet.get("AvailableIpAddressCount", 0),
                        "state": subnet.get("State"),
                        "tags": subnet.get("Tags", []),
                    }
                )

            vpcs.append(
                {
                    "vpcId": vpc_id,
                    "cidrBlock": vpc["CidrBlock"],
                    "state": vpc.get("State"),
                    "isDefault": vpc.get("IsDefault", False),
                    "tags": vpc.get("Tags", []),
                    "subnets": subnets,
                }
            )

        return {"vpcs": vpcs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nat-gateways")
def list_nat_gateways(ep: EndpointInfo = Depends(get_endpoint_info)) -> dict[str, Any]:
    """List all NAT gateways."""
    try:
        client = get_client("ec2", **ep.client_kwargs())
        paginator = client.get_paginator("describe_nat_gateways")

        gateways = []
        for gatewaySet in paginator.paginate():
            for gateway in gatewaySet.get("NatGateways", []):
                gateways.append(
                    {
                        "NatGatewayId": gateway["NatGatewayId"],
                        "CreateTime": gateway["CreateTime"],
                        "AvailabilityMode": gateway["AvailabilityMode"],
                        "AutoScalingIps": gateway.get("AutoScalingIps", "disabled"),
                        "VpcId": gateway["VpcId"],
                        "SubnetId": gateway["SubnetId"],
                        "NatGatewayAddressSet": gateway.get("NatGatewayAddressSet", []),
                        "State": gateway.get("State", ""),
                        "Tags": gateway.get("Tags", []),
                    }
                )
        return {"nat_gateways": gateways}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/internet-gateways")
def list_internet_gateways(ep: EndpointInfo = Depends(get_endpoint_info)) -> dict[str, Any]:
    """List all Internet gateways."""
    try:
        client = get_client("ec2", **ep.client_kwargs())
        paginator = client.get_paginator("describe_internet_gateways")

        gateways = []
        for gatewaySet in paginator.paginate():
            for gateway in gatewaySet.get("InternetGatewaySet", []):
                gateways.append(
                    {
                        "InternetGatewayId": gateway["InternetGatewayId"],
                        "AttachmentSet" : gateway.get("Attachments", []),
                        "Tags": gateway.get("Tags", []),
                    }
                )
        return {"internet_gateways": gateways}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))