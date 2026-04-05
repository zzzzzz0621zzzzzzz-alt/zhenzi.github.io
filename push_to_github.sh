#!/bin/bash

echo "正在推送代码到GitHub..."

# 设置用户名和邮箱（如果尚未设置）
git config --global user.name "zzzzzz0621zzzzzzz-alt"
git config --global user.email "你的邮箱@example.com"

# 尝试推送
echo "请输入你的GitHub用户名:"
read username
echo "请输入你的GitHub个人访问令牌:"
read -s token

# 使用token进行推送
git push https://${username}:${token}@github.com/zzzzzz0621zzzzzzz-alt/zhenzi.github.io.git master

echo "推送完成！"