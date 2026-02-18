#!/bin/bash
# Quick start script for OPA Test Framework

set -e

echo "🚀 OPA Test Framework - Quick Start"
echo "===================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

echo "✓ Docker and docker-compose are installed"
echo ""

# Start OPA
echo "📦 Starting OPA instance..."
docker-compose up -d opa

# Wait for OPA to be ready
echo "⏳ Waiting for OPA to be ready..."
timeout 30 bash -c 'until curl -f http://localhost:8181/health 2>/dev/null; do sleep 2; done' || {
    echo "❌ OPA failed to start"
    docker-compose logs opa
    exit 1
}

echo "✓ OPA is ready"
echo ""

# Load policies
echo "📝 Loading example policies..."
for policy in examples/policies/*.rego; do
    if [[ ! "$policy" =~ _test\.rego$ ]]; then
        policy_name=$(basename "$policy" .rego)
        echo "  Loading: $policy_name"
        curl -s -X PUT --data-binary @"$policy" \
            http://localhost:8181/v1/policies/"$policy_name" > /dev/null
    fi
done

echo "✓ Policies loaded"
echo ""

# Install Python dependencies if not already installed
if ! command -v opa-test &> /dev/null; then
    echo "📦 Installing OPA Test Framework..."
    pip install -q -r requirements.txt
    pip install -q -e .
    echo "✓ Installation complete"
    echo ""
fi

# Run smoke tests
echo "🧪 Running smoke tests..."
echo ""
OPA_URL=http://localhost:8181 opa-test --mode smoke --config config.example.yaml

echo ""
echo "✅ Quick start complete!"
echo ""
echo "Next steps:"
echo "  • Run full tests: opa-test --mode full --config config.example.yaml"
echo "  • Run specific category: opa-test --mode category --category health --config config.example.yaml"
echo "  • View OPA UI: http://localhost:8181"
echo "  • Stop OPA: docker-compose down"
echo ""
