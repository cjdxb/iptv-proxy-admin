#!/bin/bash
# IPTV Proxy Admin 版本管理脚本
# 用法: ./version.sh [patch|minor|major|<version>]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取当前版本
CURRENT_VERSION=$(node -p "require('./frontend/package.json').version")
echo -e "${BLUE}📦 当前版本: ${GREEN}${CURRENT_VERSION}${NC}"

# 检查参数
if [ -z "$1" ]; then
  echo -e "${RED}❌ 错误: 请指定版本类型或版本号${NC}"
  echo "用法: ./version.sh [patch|minor|major|<version>]"
  echo ""
  echo "示例:"
  echo "  ./version.sh patch    # 0.1.3 → 0.1.4"
  echo "  ./version.sh minor    # 0.1.3 → 0.2.0"
  echo "  ./version.sh major    # 0.1.3 → 1.0.0"
  echo "  ./version.sh 0.2.0    # 指定版本号"
  exit 1
fi

VERSION_TYPE=$1

# 进入前端目录
cd frontend

echo ""
echo -e "${YELLOW}🔄 更新前端版本号...${NC}"

# 使用 npm version 更新版本
if [[ "$VERSION_TYPE" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  # 如果是具体版本号
  npm version $VERSION_TYPE --no-git-tag-version
else
  # 如果是 patch/minor/major
  npm version $VERSION_TYPE --no-git-tag-version
fi

# 获取新版本
NEW_VERSION=$(node -p "require('./package.json').version")
echo -e "${GREEN}✅ 前端版本已更新: ${NEW_VERSION}${NC}"

# 返回项目根目录
cd ..

echo ""
echo -e "${YELLOW}🔄 更新后端版本号...${NC}"

# 创建或更新后端版本文件
cat > backend/VERSION << EOF
$NEW_VERSION
EOF

echo -e "${GREEN}✅ 后端版本已更新: ${NEW_VERSION}${NC}"

# 如果在 Git 仓库中
if [ -d ".git" ]; then
  echo ""
  echo -e "${YELLOW}📝 创建 Git 提交...${NC}"

  # 添加修改的文件
  git add frontend/package.json frontend/package-lock.json backend/VERSION

  # 创建提交
  git commit -m "chore(release): bump version to ${NEW_VERSION}"

  # 创建标签
  git tag -a "v${NEW_VERSION}" -m "Release version ${NEW_VERSION}"

  echo -e "${GREEN}✅ Git 提交和标签已创建${NC}"
  echo ""
  echo -e "${BLUE}💡 提示: 运行以下命令推送到远程仓库:${NC}"
  echo -e "   ${YELLOW}git push && git push --tags${NC}"
fi

echo ""
echo -e "${GREEN}🎉 版本更新完成!${NC}"
echo -e "${BLUE}📦 新版本: ${GREEN}${NEW_VERSION}${NC}"
echo ""
echo -e "${BLUE}📝 后续步骤:${NC}"
echo "  1. 更新 CHANGELOG.md 记录变更"
echo "  2. 重新构建前端: cd frontend && npm run build"
echo "  3. 部署新版本"
echo "  4. 推送到 Git: git push && git push --tags"
