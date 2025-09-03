# LLM Agent Backend Infrastructure - Connection Information

## Azure Resources Created

### Subscription Details
- **Subscription**: Microsoft Azure Sponsorship  
- **Subscription ID**: c57910e6-96a8-4083-b94f-e1eb353cfb19
- **Resource Group**: functional_ai
- **Location**: East US
- **User Account**: rajsuthan777@gmail.com

### Virtual Machine
- **Name**: llm-agent-vm
- **Size**: Standard_B2s (2 vCPUs, 4 GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Public IP**: 172.190.13.51
- **Private IP**: 10.0.0.4  
- **FQDN**: llm-agent-api.eastus.cloudapp.azure.com
- **SSH Access**: Port 22 (open)
- **API Port**: Port 8000 (open)
- **Admin Username**: azureuser
- **SSH Key Location**: ~/.ssh/id_rsa

### Storage Account
- **Name**: functionalaistorage
- **Type**: StorageV2
- **Replication**: Standard_LRS
- **Access Tier**: Hot
- **Primary Key**: 35N7QOp+WIphG9CD9zdtmd9N15tZRJ7NID4i6CHLxP4a09FTBzU/9hHOrnCjJFWtIj+how8vArIZ+AStLA1RVA==
- **Secondary Key**: eD1KChJm5Ywdx/dcrTOaYO1lmCOEVCoe8qw5P4ODlCZc0LZvjMDxE8V14yySJ9/lYI93mgytQg1D+AStsmEJSQ==

### Storage Containers & Queues
- **Blob Container**: codebase-projects (for storing project zip files)
- **Blob Container**: codebase-docs (existing documentation)  
- **Queue**: llm-jobs (for job processing)

## Connection Strings

### Azure Storage Connection String
```
DefaultEndpointsProtocol=https;AccountName=functionalaistorage;AccountKey=35N7QOp+WIphG9CD9zdtmd9N15tZRJ7NID4i6CHLxP4a09FTBzU/9hHOrnCjJFWtIj+how8vArIZ+AStLA1RVA==;EndpointSuffix=core.windows.net
```

## SSH Connection
```bash
ssh azureuser@llm-agent-api.eastus.cloudapp.azure.com
# or
ssh azureuser@172.190.13.51
```

## API Endpoint (once deployed)
```
http://llm-agent-api.eastus.cloudapp.azure.com:8000
```

## Cost Estimates
- **VM (Standard_B2s)**: ~$30-35/month (24/7) or ~$10-15/month (deallocated when not in use)
- **Storage**: ~$2-5/month
- **Network**: ~$2-5/month
- **Total**: Under $50/month (with smart deallocation: $20-25/month)

## Worker Configuration
- **Worker Count**: 5 workers (2 × 2 vCPUs + 1)
- **Project Cache**: /projects directory
- **Results**: /results directory

## Next Steps
1. SSH into VM and install dependencies
2. Deploy FastAPI application and worker processes  
3. Test the complete system
4. Configure auto-start services

## Security Notes
- SSH keys are stored locally in ~/.ssh/
- Storage account keys should be kept secure
- VM has network security group restricting access to ports 22 and 8000 only