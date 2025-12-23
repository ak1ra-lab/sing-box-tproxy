# 架构设计

本文档详细说明 sing-box-tproxy 的技术架构, 透明代理原理以及各组件交互机制.

## 目录

- [系统架构](#system-architecture)
- [部署拓扑](#deployment-topology)
- [透明代理原理](#transparent-proxy-principle)
- [fwmark 机制](#fwmark-mechanism)
- [策略路由详解](#policy-routing-details)
- [nftables 规则解析](#nftables-rules-analysis)
- [模式对比](#mode-comparison)
- [技术细节](#technical-details)
- [参考资料](#references)

## 系统架构 {#system-architecture}

sing-box-tproxy 由以下核心组件构成:

```mermaid
graph TB
    A[sing-box-tproxy Stack] --> B[sing-box<br/>proxy service]
    A --> C[nftables<br/>packet filtering]
    A --> D[Policy Route<br/>fwmark routing]
    B <--> E[TPROXY Port 7895]
    C <--> E
    D <--> E
    E --> F[Linux Kernel<br/>Netfilter/Routing]
    F --> G[Network Interface]
```

### 组件职责

| Component        | Responsibility                  | Implementation     |
| ---------------- | ------------------------------- | ------------------ |
| sing-box         | Proxy service, protocol handler | systemd service    |
| nftables         | Traffic filtering, fwmark       | inet table, chains |
| Policy routing   | fwmark-based routing            | iproute2, netplan  |
| Config generator | Subscription parser             | Python tool        |
| Auto updater     | Periodic subscription update    | systemd timer      |

## 部署拓扑 {#deployment-topology}

### gateway 模式

```mermaid
graph TB
    Internet((Internet))
    GW[sing-box Gateway<br/>10.0.42.253]
    PC1[PC-1<br/>10.0.42.10]
    PC2[PC-2<br/>10.0.42.20]
    Phone[Phone<br/>10.0.42.30]

    Internet --- GW
    GW --- LAN{LAN Switch}
    LAN --- PC1
    LAN --- PC2
    LAN --- Phone
```

流量路径:

```
PC-1 → gateway → nftables (prerouting) → fwmark 224 → TPROXY → sing-box → Internet
```

### Local 模式

```mermaid
graph TB
    Internet((Internet))
    WS[Workstation<br/>with sing-box]

    Internet --- WS
```

流量路径:

```
App → nftables (output) → fwmark 224 → TPROXY → sing-box → Internet
```

## 透明代理原理 {#transparent-proxy-principle}

透明代理基于 Linux 内核特性:

1. Netfilter/nftables - packet filtering and marking
2. Policy routing - fwmark-based routing decision
3. TPROXY - transparent TCP/UDP hijacking

### 数据流处理过程

```mermaid
flowchart TD
    A[Application] -->|1. Send packet| B[Netfilter nftables]
    B -->|2. Check rules<br/>Mark fwmark=224| C[Policy routing]
    C -->|3. Lookup table 224| D[Routing table 224<br/>local default dev lo]
    D -->|4. Route to local| E[TPROXY Port 7895]
    E -->|5. Hijack connection<br/>Apply proxy rules| F[sing-box outbound<br/>proxy user, fwmark=225]
    F -->|6. Bypass tproxy rules<br/>To Internet| G((Internet))
```

## fwmark 机制 {#fwmark-mechanism}

项目使用两个 fwmark 值实现防回环的透明代理:

### PROXY_MARK (224)

用途: 标记需要通过 TPROXY 代理的普通应用流量

触发条件:

- 非本地流量 (非 127.0.0.0/8)
- 非保留地址 (非 RFC 1918 私有地址等)
- 非用户自定义排除地址
- TCP/UDP 协议

nftables 规则:

```nft
# output_tproxy chain
meta l4proto { tcp, udp } meta mark set $PROXY_MARK
```

策略路由配置:

```yaml
# /etc/netplan/99-sing_box_tproxy.yaml
routing-policy:
  - from: 0.0.0.0/0
    mark: 224
    table: 224
```

路由表:

```shell
# ip route show table 224
local default dev lo scope host
```

### ROUTE_DEFAULT_MARK (225)

用途: 标记 sing-box 自身发出的流量, 避免被再次代理造成循环

工作原理:

1. sing-box 以 proxy 用户 (UID=13, GID=13) 身份运行
2. 该用户发出的所有流量被标记为 225
3. nftables 规则直接放行, 不进入 TPROXY 处理

nftables 规则:

```nft
meta skuid $PROXY_UID meta skgid $PROXY_GID \
  meta mark set $ROUTE_DEFAULT_MARK accept
```

为什么需要独立用户:

- 无法仅通过 PID 或进程名过滤 (进程可能 fork)
- UID/GID 是内核级别的稳定标识
- 简化 nftables 规则, 性能更优

### 双 fwmark 防回环机制

单 fwmark 循环问题:

```mermaid
flowchart LR
    A[App send packet] --> B[nftables mark fwmark=224]
    B --> C[Route to TPROXY table 224]
    C --> D[sing-box process and send]
    D --> B
```

双 fwmark 解决方案:

```mermaid
flowchart TD
    A[App] --> B[nftables<br/>mark=224]
    B --> C[table 224]
    C --> D[TPROXY]
    D --> E[sing-box<br/>UID=13]
    E --> F[nftables<br/>detect UID=13<br/>mark=225, accept]
    F --> G[main table]
    G --> H((Internet))
```

实现关键:

1. sing-box 使用独立系统用户运行 (UID=13)
2. UID/GID 是内核级稳定标识
3. nftables 优先匹配 UID, 直接放行 sing-box 流量

## 策略路由详解 {#policy-routing-details}

策略路由 (Policy-based Routing) 允许基于数据包属性 (如 fwmark, 源地址) 选择路由表, 而非仅依赖目标地址.

### 路由表定义

```shell
# /etc/iproute2/rt_tables.d/sing_box_tproxy.conf
224 sing_box_tproxy
```

定义编号为 224 的自定义路由表, 名称为 `sing_box_tproxy`.

### 策略规则

```shell
# ip rule show
0:      from all lookup local
32765:  from all fwmark 0xe0 lookup 224  # 0xe0 = 224 (hex)
32766:  from all lookup main
32767:  from all lookup default
```

规则解读:

- 优先级 32765: fwmark=224 的数据包查询表 224
- 其他数据包使用 main 表 (正常路由)

### 路由表内容

```shell
# ip route show table 224
local default dev lo scope host
```

关键配置解析:

| Parameter | Meaning                                     |
| --------- | ------------------------------------------- |
| local     | Route type: treat destination as local      |
| default   | Match all destinations (0.0.0.0/0)          |
| dev lo    | Output interface: loopback (not real route) |

为什么使用 local 路由:

1. 允许绑定远程地址: TPROXY 需要绑定原始目标地址 (如 8.8.8.8:53)
2. 配合 SO_TRANSPARENT: 套接字选项允许绑定非本地地址
3. 防止真正路由: dev lo 确保数据包不会被发送到物理接口

### Netplan 配置示例

```yaml
# /etc/netplan/99-sing_box_tproxy.yaml
network:
  version: 2
  ethernets:
    eth0:
      routes:
        - to: 0.0.0.0/0
          type: local
          table: 224
      routing-policy:
        - from: 0.0.0.0/0
          mark: 224
          table: 224
```

等价命令:

```shell
ip route add local default dev lo table 224
ip rule add fwmark 224 table 224
```

## nftables 规则解析 {#nftables-rules-analysis}

### 核心表结构

```nft
table inet sing_box_tproxy {
    # 定义常量
    define TPROXY_PORT = 7895
    define PROXY_MARK = 224
    define ROUTE_DEFAULT_MARK = 225
    define PROXY_UID = 13
    define PROXY_GID = 13
    define INTERFACE = "eth0"

    # IP 地址集合
    set reserved_ip4 {
        type ipv4_addr
        flags interval
        elements = {
            0.0.0.0/8, 10.0.0.0/8, 127.0.0.0/8,
            169.254.0.0/16, 172.16.0.0/12, 192.168.0.0/16,
            224.0.0.0/4, 240.0.0.0/4
        }
    }

    set custom_bypassed_ip4 {
        type ipv4_addr
        flags interval
        # 用户自定义排除地址
    }

    chain prerouting_tproxy { ... }  # gateway 模式
    chain output_tproxy { ... }      # 所有模式
}
```

### prerouting_tproxy

处理来自 LAN 设备的转发流量.

```nft
chain prerouting_tproxy {
    type filter hook prerouting priority mangle;
    policy accept;

    # DNS hijack (highest priority, ensure LAN DNS captured)
    meta l4proto { tcp, udp } th dport 53 \
        tproxy to :$TPROXY_PORT accept

    # Reject direct access to tproxy port
    fib daddr type local meta l4proto { tcp, udp } \
        th dport $TPROXY_PORT reject with icmpx type host-unreachable

    # Bypass local and reserved addresses
    fib daddr type local accept
    ip daddr @reserved_ip4 accept

    # Bypass custom addresses
    ip daddr @custom_bypassed_ip4 accept

    # Bypass established transparent proxy connections
    meta l4proto tcp socket transparent 1 \
        meta mark set $PROXY_MARK accept

    # Transparent proxy other traffic
    meta l4proto { tcp, udp } \
        tproxy to :$TPROXY_PORT meta mark set $PROXY_MARK
}
```

规则执行顺序:

1. **DNS 请求直接劫持** (最高优先级)

   - 确保局域网 DNS 请求被正确捕获
   - 必须在任何绕过规则之前执行
   - 防止 DNS 请求被本地或保留地址规则提前放行

2. **拒绝直接访问 TPROXY 端口** (防止回环攻击)

   - 阻止恶意客户端直接连接 7895 端口
   - 防止意外的服务发现和安全风险

3. **本地流量和保留地址放行** (最常见的排除场景)

   - `fib daddr type local`: 本地地址 (127.0.0.0/8)
   - `@reserved_ip4`: RFC 定义的私有/保留地址
   - 规则紧密相邻, 利于 CPU 缓存

4. **用户自定义排除地址放行**

   - 支持动态添加自定义绕过规则
   - 通过 `nft` 命令管理 `custom_bypassed_ip4` 集合

5. **已建立的透明代理连接标记后放行**

   - `socket transparent 1`: 检测已被 TPROXY 劫持的连接
   - 避免重复处理, 提升性能

6. **其他流量 TPROXY + 标记**
   - 最终匹配所有需要代理的流量
   - 同时设置 fwmark 用于策略路由

关键设计:

- **DNS 规则必须放在最前面**: 在 gateway 模式下, 来自局域网的 DNS 请求必须在任何绕过规则之前被捕获, 否则可能被 `fib daddr type local` 或 `@reserved_ip4` 规则提前放行导致 DNS 解析失败
- 提前拒绝无效流量, 减少后续规则检查
- 本地和保留地址检查紧密相邻, 利于 CPU 缓存

### output_tproxy

处理本机应用发出的流量.

```nft
chain output_tproxy {
    type route hook output priority mangle;
    policy accept;

    # Bypass non-default interface traffic
    oifname != $INTERFACE accept

    # Bypass sing-box own traffic (critical, highest priority for default interface)
    meta skuid $PROXY_UID meta skgid $PROXY_GID \
        meta mark set $ROUTE_DEFAULT_MARK accept

    # Bypass already marked traffic
    meta mark $ROUTE_DEFAULT_MARK accept

    # DNS hijack (before local/reserved address check)
    meta l4proto { tcp, udp } th dport 53 \
        meta mark set $PROXY_MARK accept

    # Bypass NetBIOS and SMB
    udp dport { netbios-ns, netbios-dgm, netbios-ssn, microsoft-ds } accept

    # Bypass local and reserved addresses
    fib daddr type local accept
    ip daddr @reserved_ip4 accept

    # Bypass custom addresses
    ip daddr @custom_bypassed_ip4 accept

    # Mark other traffic
    meta l4proto { tcp, udp } meta mark set $PROXY_MARK
}
```

规则优化:

1. **规则 1: 网卡过滤优先级最高**

   - 快速排除非目标接口流量 (如 docker0, lo)
   - 减少不必要的规则遍历

2. **规则 2: UID/GID 检查次之**

   - sing-box 持续产生大量出站流量
   - 提前匹配可减少 90%+ 后续规则检查开销

3. **规则 3: 绕过已标记流量**

   - 防止重复标记
   - 配合其他工具使用 fwmark 225 时自动放行

4. **规则 4: DNS 规则前置**

   - 必须在本地/保留地址检查之前
   - 确保本机 DNS 请求 (如 127.0.0.53:53) 被正确代理
   - 避免被 `fib daddr type local` 规则提前放行

5. **规则 5: 绕过 NetBIOS 和 SMB**

   - 端口: 137 (netbios-ns), 138 (netbios-dgm), 139 (netbios-ssn), 445 (microsoft-ds)
   - 防止局域网文件共享流量被代理
   - Windows 网络发现和文件共享正常工作

6. **规则 6-7: 本地和保留地址检查**

   - CPU 缓存友好, 减少内存访问
   - 处理常见的本地流量场景

7. **规则 8: 用户自定义排除地址**

   - 灵活扩展性

8. **规则 9: 标记其他流量**
   - 最终匹配所有需要代理的流量
   - 仅标记不使用 TPROXY (配合策略路由工作)

关键优化:

- **网卡过滤最优先**: 快速排除非目标接口流量
- **UID/GID 检查次之**: 大幅减少 sing-box 自身流量的规则遍历开销
- **DNS 规则前置**: 确保本机 DNS 请求 (如 systemd-resolved 的 127.0.0.53:53) 被正确代理
- **NetBIOS/SMB 排除**: 保证局域网文件共享和服务发现正常工作
- **本地和保留地址检查合并**: CPU 缓存友好
- **仅标记不使用 TPROXY**: output 链配合策略路由工作

### nftables vs iptables

| Feature        | nftables                  | iptables (legacy)  |
| -------------- | ------------------------- | ------------------ |
| Table/Chain    | Custom tables and chains  | Fixed (nat/mangle) |
| Syntax         | BPF-like, concise         | Verbose options    |
| Performance    | Higher (set optimization) | Lower              |
| IPv4/IPv6      | Unified (inet family)     | Separate rules     |
| Atomic updates | Yes                       | No                 |

## 模式对比 {#mode-comparison}

### 功能对比表

| Feature        | mixed     | local      | gateway |
| -------------- | --------- | ---------- | ------- |
| Transparent    | No        | Local only | Network |
| prerouting     | No        | Yes        | Yes     |
| output chain   | No        | Yes        | Yes     |
| IP forwarding  | No        | No         | Yes     |
| Policy routing | No        | Yes        | Yes     |
| TPROXY listen  | N/A       | 127.0.0.1  | 0.0.0.0 |
| HTTP/SOCKS     | 127.0.0.1 | 127.0.0.1  | 0.0.0.0 |
| Toggle script  | No        | Yes        | No      |

### 配置差异

Mixed 模式:

- 无 nftables 规则
- 无策略路由配置
- 仅提供 HTTP/SOCKS5 监听 (127.0.0.1)
- 应用需手动配置代理

Local 模式:

- 完整 nftables 规则集 (prerouting + output)
- 启用策略路由处理本机流量
- TPROXY 监听 127.0.0.1:7895
- IP forwarding 关闭 (net.ipv4.ip_forward=0)
- 提供 sing-box-tproxy-toggle.sh 脚本切换透明代理

gateway 模式 (默认):

- 完整 nftables 规则集 (prerouting + output)
- 启用策略路由处理本机和转发流量
- TPROXY 监听 0.0.0.0:7895
- HTTP/SOCKS 监听 0.0.0.0
- IP forwarding 开启 (net.ipv4.ip_forward=1)
- 处理来自 LAN 设备的转发流量

关键差异说明:

1. TPROXY 监听地址:

   - local 模式: 监听 127.0.0.1 (仅处理本机流量)
   - gateway 模式: 监听 0.0.0.0 (处理本机和转发流量)
   - gateway 模式必须监听 0.0.0.0: nftables TPROXY 机制虽在内核层劫持, 但来自局域网设备的流量源地址非 127.0.0.1, 若 sing-box 仅监听 127.0.0.1 则无法正确处理
   - nftables 显式拒绝直接访问 TPROXY 端口的流量 (防回环)

2. local vs gateway 唯一区别:

   - IP forwarding 开关 (sysctl net.ipv4.ip_forward)
   - gateway 模式处理转发流量, local 模式仅处理本机流量
   - nftables 规则集完全相同

3. Toggle 脚本仅用于 local 模式:
   - 工作站/笔记本需要灵活切换透明代理
   - gateway 模式通常持续运行, 无需切换

### 部署选型建议

| Scenario           | Mode    | Reason                         |
| ------------------ | ------- | ------------------------------ |
| Dev/test server    | mixed   | Minimal invasion, manual proxy |
| Workstation/laptop | local   | Transparent + flexible toggle  |
| Home gateway       | gateway | Network-wide transparent proxy |
| Container env      | mixed   | Avoid network complexity       |
| VPS single user    | local   | Transparent proxy without LAN  |

## 技术细节 {#technical-details}

### TPROXY vs REDIRECT

| Feature       | TPROXY         | REDIRECT         |
| ------------- | -------------- | ---------------- |
| Protocol      | TCP + UDP      | TCP only         |
| Destination   | Original addr  | Rewrite to local |
| NAT type      | Full Cone      | DNAT required    |
| Kernel option | SO_TRANSPARENT | SO_ORIGINAL_DST  |
| Performance   | Better         | Slightly lower   |

REDIRECT 劣势:

- 仅支持 TCP,无法处理 UDP (DNS, QUIC 等)
- 目标地址被改写,需额外系统调用获取原始地址

### Netplan 配置原理

```yaml
routes:
  - to: 0.0.0.0/0
    type: local
    table: 224

routing-policy:
  - from: 0.0.0.0/0
    mark: 224
    table: 224
```

等价于:

```shell
ip route add local default dev lo table 224
ip rule add fwmark 224 table 224
```

为什么使用 netplan:

- 声明式配置, 重启后自动应用
- 避免手动编写 systemd 脚本
- 与 Ubuntu/Debian 系统集成

## 参考资料 {#references}

- [sing-box 官方文档](https://sing-box.sagernet.org/)
- [sing-box tproxy inbound](https://sing-box.sagernet.org/configuration/inbound/tproxy/)
- [sing-box tproxy 透明代理教程](https://lhy.life/20231012-sing-box-tproxy/)
- [nftables wiki](https://wiki.nftables.org/)
- [Linux Policy Routing](https://www.kernel.org/doc/html/latest/networking/policy-routing.html)
