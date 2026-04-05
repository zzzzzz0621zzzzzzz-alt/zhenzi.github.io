#!/bin/bash
echo "检查GitHub仓库状态..."
curl -s https://api.github.com/repos/zzzzzz0621zzzzzzz-alt/zhenzi.github.io/commits | grep -o '"sha": "[^"]*' | head -5