# 重置 (Reset) sing-box 部署

`playbooks/sing_box_reset.yaml` 与 `roles/sing_box_reset` 用于撤销 `sing_box_tproxy` 或 `sing_box_server` playbook 所做的变更.

## 用法

通过 `-e sing_box_reset_profile=<profile>` 指定要重置的部署类型 (`tproxy` 或 `server`):

```shell
# 重置透明代理节点 (tproxy)
ansible-playbook playbooks/sing_box_reset.yaml \
    -e sing_box_reset_profile=tproxy

# 重置服务端节点 (server)
ansible-playbook playbooks/sing_box_reset.yaml \
    -e sing_box_reset_profile=server
```

## 常用选项

```shell
# 仅清理 systemd 单元与配置文件, 保留 APT 包
ansible-playbook playbooks/sing_box_reset.yaml \
    -e sing_box_reset_profile=tproxy \
    -e sing_box_reset_remove_packages=false

# 针对单台主机而不是整个 inventory 组
ansible-playbook playbooks/sing_box_reset.yaml \
    -e sing_box_reset_profile=tproxy \
    -e playbook_hosts=sing-box-tproxy-node01
```

## 各模式清理范围

### tproxy 模式

清理 `sing_box_install`, `sing_box_config` 和 `sing_box_tproxy` 部署的全部内容:

- 停止并卸载 sing-box 及相关 systemd service/timer 单元
- 清理 sing-box-config 定时器和 liveness-probe 服务单元
- 移除 nftables 规则集
- 移除 iproute2 策略路由表
- 删除 netplan 配置文件
- 删除 APT 软件包和 APT 源 (除非 `sing_box_reset_remove_packages=false`)
- 删除运行时目录 (`sing_box_etc_dir`, `sing_box_state_dir`, `sing_box_log_dir`)

### server 模式

清理 `sing_box_install` 部署的公共内容:

- 停止并卸载 sing-box systemd service 单元
- 删除 APT 软件包和 APT 源 (除非 `sing_box_reset_remove_packages=false`)
- 删除 `sing_box_etc_dir` 目录 (包含 `config.json`)

> **注意**: 本地 `config/client_outbounds/` 中已生成的客户端配置文件**不会**被 reset 操作删除.

## 相关文档

- [透明代理 (tproxy) 部署](deploy-tproxy.md)
- [服务端 (server) 部署](deploy-server.md)
