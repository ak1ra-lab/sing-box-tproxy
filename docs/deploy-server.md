# 服务端 (server) 部署指南

本文档介绍如何使用本项目在一台 Debian/Ubuntu 主机上部署 sing-box 服务端 (Shadowsocks, Trojan, Hysteria2 等).

## 前置要求

- 目标主机: Debian/Ubuntu Linux, 具有公网 IP 或域名
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

为 `sing-box-server` 组创建 group_vars:

```shell
mkdir -p playbooks/group_vars/sing-box-server
cp roles/sing_box_server/defaults/main.yaml playbooks/group_vars/sing-box-server/main.yaml
vim playbooks/group_vars/sing-box-server/main.yaml
```

公共配置项定义在 group_vars 中; 主机特有的配置项 (如 region, hostname) 定义在 host_vars 中.

### 4. 创建 host_vars (可选)

```shell
mkdir -p playbooks/host_vars/sing-box-server-node01
# vim playbooks/host_vars/sing-box-server-node01/main.yaml
```

### 5. 管理 group_vars patch

```shell
./group_vars.sh gen server   # 生成 / 刷新 patch
./group_vars.sh sync server  # 同步上游变更后重新应用 patch
```

### 6. 执行 playbook

```shell
ansible-playbook playbooks/sing_box_server.yaml -v
```

playbook 执行完成后会在本地 `config/client_outbounds/` 目录下生成客户端配置文件.

## 服务端协议配置

支持的协议通过变量开关控制:

| 变量                                 | 默认值  | 说明              |
| ------------------------------------ | ------- | ----------------- |
| `sing_box_server_enable_shadowsocks` | `true`  | Shadowsocks 入站  |
| `sing_box_server_enable_trojan`      | `true`  | Trojan 入站 (TLS) |
| `sing_box_server_enable_hysteria2`   | `true`  | Hysteria2 入站    |
| `sing_box_server_enable_vless`       | `false` | VLESS 入站 (TLS)  |
| `sing_box_server_enable_tuic`        | `false` | TUIC 入站         |

密码与用户若不指定则自动生成. 通过 `sing_box_server_user_count` 控制生成用户数量 (默认 1).

## TLS 配置

通过 `sing_box_server_tls_mode` 选择证书管理方式:

| 模式     | 说明                                             |
| -------- | ------------------------------------------------ |
| `acme`   | 自动申请 Let's Encrypt 证书 (需要域名和开放 443) |
| `manual` | 手动提供证书文件路径                             |

ACME 模式需要设置:

```yaml
sing_box_server_hostname: "my.example.com"
sing_box_server_acme_email: "admin@example.com"
```

## 配合 tproxy 使用

服务端部署完成后, 将生成的客户端配置以 `local` 类型订阅引用到 tproxy 客户端中:

```yaml
# playbooks/group_vars/sing-box-tproxy/main.yaml
sing_box_subscriptions:
  sing-box-server-node01:
    type: local
    format: sing-box
    enabled: true
    path: "config/client_outbounds/sing-box-server-node01.outbounds.json"
```

执行 `sing_box_tproxy.yaml` 时会自动将 `config/client_outbounds/` 同步到目标主机的 `/var/lib/sing-box/config/client_outbounds/`.

## 相关文档

- [Ansible 变量说明](ansible_vars.md)
- [透明代理 (tproxy) 部署](deploy-tproxy.md)
- [重置 sing-box 部署](reset.md)
