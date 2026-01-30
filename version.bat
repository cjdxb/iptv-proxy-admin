@echo off
REM IPTV Proxy Admin 版本管理脚本 (Windows)
REM 用法: version.bat [patch|minor|major|<version>]

setlocal enabledelayedexpansion

REM 检查参数
if "%1"=="" (
    echo [错误] 请指定版本类型或版本号
    echo.
    echo 用法: version.bat [patch^|minor^|major^|^<version^>]
    echo.
    echo 示例:
    echo   version.bat patch    # 0.1.3 -^> 0.1.4
    echo   version.bat minor    # 0.1.3 -^> 0.2.0
    echo   version.bat major    # 0.1.3 -^> 1.0.0
    echo   version.bat 0.2.0    # 指定版本号
    exit /b 1
)

set VERSION_TYPE=%1

REM 获取当前版本
cd frontend
for /f "delims=" %%i in ('node -p "require('./package.json').version"') do set CURRENT_VERSION=%%i
echo [当前版本] %CURRENT_VERSION%
echo.

REM 更新前端版本
echo [更新中] 更新前端版本号...
npm version %VERSION_TYPE% --no-git-tag-version

if errorlevel 1 (
    echo [错误] 更新前端版本失败
    exit /b 1
)

REM 获取新版本
for /f "delims=" %%i in ('node -p "require('./package.json').version"') do set NEW_VERSION=%%i
echo [成功] 前端版本已更新: %NEW_VERSION%
echo.

REM 返回项目根目录
cd ..

REM 更新后端版本
echo [更新中] 更新后端版本号...
echo %NEW_VERSION% > backend\VERSION
echo [成功] 后端版本已更新: %NEW_VERSION%
echo.

REM 检查是否在 Git 仓库中
if exist ".git" (
    echo [Git] 创建提交...
    git add frontend/package.json frontend/package-lock.json backend/VERSION
    git commit -m "chore(release): bump version to %NEW_VERSION%"
    git tag -a "v%NEW_VERSION%" -m "Release version %NEW_VERSION%"
    echo [成功] Git 提交和标签已创建
    echo.
    echo [提示] 运行以下命令推送到远程仓库:
    echo   git push ^&^& git push --tags
    echo.
)

echo [完成] 版本更新完成!
echo [新版本] %NEW_VERSION%
echo.
echo [后续步骤]
echo   1. 更新 CHANGELOG.md 记录变更
echo   2. 重新构建前端: cd frontend ^&^& npm run build
echo   3. 部署新版本
echo   4. 推送到 Git: git push ^&^& git push --tags

endlocal
