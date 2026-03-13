# 透明代理 (tproxy) 部署指南

本文档介绍如何使用本项目将一台 Debian/Ubuntu 主机部署为 sing-box TPROXY 透明代理网关或本机代理.

## 前置要求

- 目标主机: Debian/Ubuntu Linux
- Ansible core >= 2.18

## 部署步骤

### 1. 克隆仓库

```shell
git clone https://github.com/ak1ra-lab/sing-box-tproxy.git
cd sing-box-tproxy/
```

### 2. 配置 Ansible inventory

参考示例 inventory 编辑适用于自己环境的配置:

```shell
cp inventory/hosts.example.yaml inventory/hosts.yaml
vim inventory/hosts.yaml
```

### 3. 创建 group_vars

为 `sing-box-tproxy` 组创建 group_vars, 将默认配置作为模板:

```shell
mkdir -p playbooks/group_vars/sing-box-tproxy
cp roles/sing_box_defaults/defaults/main.yaml playbooks/group_vars/sing-box-tproxy/main.yaml
vim playbooks/group_vars/sing-box-tproxy/main.yaml
```

公共配置项 (如节点订阅 `sing_box_subscriptions`) 定义在 group_vars 中; 主机特有的私有配置项定义在 host_vars 中 (tproxy 场景通常不需要 host_vars).

### 4. 管理 group_vars patch

完成变更后生成 patch 文件, 以便后续同步上游时复用:

```shell
./group_vars.sh gen tproxy
```

当 `roles/sing_box_defaults/defaults/main.yaml` 有上游变更需要同步时:

```shell
./group_vars.sh sync tproxy
```

### 5. 执行 playbook

```shell
ansible-playbook playbooks/sing_box_tproxy.yaml -v
```

### 6. 验证部署

登录目标主机, 检查各组件状态:

```shell
ssh sing-box-tproxy-node01

systemctl status sing-box*
nft list ruleset
ip rule
ip route show table 224
```

## 订阅配置示例

在 group_vars 中配置节点订阅 (`sing_box_subscriptions`):

```yaml
sing_box_subscriptions:
  # 远程 SIP002 格式订阅
  my_provider:
    type: remote
    format: sip002
    enabled: true
    url: "https://sub.example.com/api/v1/client/subscribe?token=YOUR_TOKEN_HERE"
    exclude: "过期|Expire|流量|Traffic"

  # 本地 sing-box 格式文件 (路径相对于 sing-box WorkingDirectory: /var/lib/sing-box)
  sing-box-server-node01:
    type: local
    format: sing-box
    enabled: true
    path: "config/client_outbounds/sing-box-server-node01.outbounds.json"
```

## 部署模式

通过 `sing_box_mode` 变量选择运行模式:

| 模式      | 适用场景         | 说明                                                 |
| --------- | ---------------- | ---------------------------------------------------- |
| `gateway` | 家庭/办公室网关  | 默认模式. 开启 IP Forwarding, 代理 LAN 所有设备      |
| `local`   | 个人工作站       | 仅代理本机流量, 关闭 IP Forwarding                   |
| `mixed`   | 开发/测试环境    | 仅启用混合代理端口, 无 nftables/路由规则             |

```yaml
# playbooks/group_vars/sing-box-tproxy/main.yaml
sing_box_mode: gateway
```

## 使用本地服务端配置

如果已通过 `sing_box_server` playbook 部署了服务端, 执行 `sing_box_tproxy` playbook 时会自动将本地 `config/client_outbounds/` 目录同步到目标主机的 `/var/lib/sing-box/config/client_outbounds/`.

在 group_vars 中以 `local` 类型订阅引用:

```yaml
sing_box_subscriptions:
  sing-box-server-node01:
    type: local
    format: sing-box
    enabled: true
    path: "config/client_outbounds/sing-box-server-node01.outbounds.json"
```

## 相关文档

- [Ansible 变量说明](ansible_vars.md)
- [架构设计与透明代理原理](architecture.md)
- [重置 sing-box 部署](reset.md)
