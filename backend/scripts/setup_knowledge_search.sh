#!/bin/bash
# Setup script for knowledge search feature

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up knowledge search feature...${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo -e "${YELLOW}Creating sample .env file...${NC}"
    echo "# Knowledge search configuration
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment" > .env
    echo -e "${YELLOW}Please edit .env file with your API keys${NC}"
    exit 1
fi

# Check if required environment variables are set
if ! grep -q "OPENAI_API_KEY" .env || ! grep -q "PINECONE_API_KEY" .env || ! grep -q "PINECONE_ENVIRONMENT" .env; then
    echo -e "${RED}Error: Required environment variables not found in .env file${NC}"
    echo -e "${YELLOW}Please add the following to your .env file:${NC}"
    echo "OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment"
    exit 1
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Initialize Pinecone index
echo -e "${YELLOW}Initializing Pinecone index...${NC}"
python scripts/setup_knowledge_base.py

# Ask if user wants to backfill existing notes
echo -e "${YELLOW}Do you want to backfill existing notes? (y/n)${NC}"
read -r backfill

if [[ $backfill == "y" || $backfill == "Y" ]]; then
    echo -e "${YELLOW}Enter user ID (leave empty for all users):${NC}"
    read -r user_id
    
    if [ -z "$user_id" ]; then
        echo -e "${YELLOW}Backfilling notes for all users...${NC}"
        python scripts/setup_knowledge_base.py
    else
        echo -e "${YELLOW}Backfilling notes for user $user_id...${NC}"
        python scripts/setup_knowledge_base.py --user="$user_id"
    fi
fi

echo -e "${GREEN}Knowledge search setup complete!${NC}"
echo -e "${YELLOW}You can now use the knowledge search feature in the application.${NC}"
echo -e "${YELLOW}To test the search functionality, run:${NC}"
echo "python scripts/test_knowledge_search.py --user=1 --query=\"your search query\"" 