#!/bin/bash

# Test script to verify bot selection functionality
echo "🧪 Testing Bot Selection Functionality"
echo "======================================"

# Test 1: Check if bot directories are detected
echo ""
echo "Test 1: Bot Directory Detection"
if [ -d "community_bots" ]; then
    echo "✅ community_bots directory exists"
    
    BOT_DIRS=()
    for dir in community_bots/*/; do
        if [ -d "$dir" ]; then
            bot_name=$(basename "$dir")
            BOT_DIRS+=("$bot_name")
            echo "   Found bot: $bot_name"
        fi
    done
    
    if [ ${#BOT_DIRS[@]} -gt 0 ]; then
        echo "✅ Found ${#BOT_DIRS[@]} bot(s)"
    else
        echo "❌ No bots found in community_bots/"
    fi
else
    echo "❌ community_bots directory not found"
fi

# Test 2: Check if index_config.json exists for reminder_bot
echo ""
echo "Test 2: Index Configuration"
if [ -f "community_bots/reminder_bot/index_config.json" ]; then
    echo "✅ index_config.json found for reminder_bot"
    
    # Try to parse with jq if available
    if command -v jq &> /dev/null; then
        bot_name=$(jq -r '.bot_name' community_bots/reminder_bot/index_config.json 2>/dev/null)
        index_count=$(jq '.indexes | length' community_bots/reminder_bot/index_config.json 2>/dev/null)
        echo "   Bot name: $bot_name"
        echo "   Index count: $index_count"
    else
        echo "   ⚠️  jq not available, skipping JSON parsing test"
    fi
else
    echo "❌ index_config.json not found for reminder_bot"
fi

# Test 3: Check if bot source directory exists
echo ""
echo "Test 3: Bot Source Directory"
if [ -d "community_bots/reminder_bot/bot" ]; then
    echo "✅ Bot source directory exists"
    file_count=$(ls -1 community_bots/reminder_bot/bot/*.py 2>/dev/null | wc -l)
    echo "   Python files: $file_count"
else
    echo "❌ Bot source directory not found"
fi

# Test 4: Check Terraform configuration
echo ""
echo "Test 4: Terraform Configuration"
if [ -f "terraform/variables.tf" ]; then
    if grep -q "bot_source_path" terraform/variables.tf; then
        echo "✅ bot_source_path variable found in variables.tf"
    else
        echo "❌ bot_source_path variable not found in variables.tf"
    fi
else
    echo "❌ terraform/variables.tf not found"
fi

if [ -f "terraform/functions.tf" ]; then
    if grep -q "var.bot_source_path" terraform/functions.tf; then
        echo "✅ bot_source_path variable used in functions.tf"
    else
        echo "❌ bot_source_path variable not used in functions.tf"
    fi
else
    echo "❌ terraform/functions.tf not found"
fi

echo ""
echo "🎉 Bot Selection Test Complete!"
echo "================================"