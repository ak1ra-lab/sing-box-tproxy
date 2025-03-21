# sing-box tproxy config

## [install sing-box](https://sing-box.sagernet.org/installation/package-manager/)

```shell
(
    sudo curl -fsSL https://sing-box.app/gpg.key -o /etc/apt/keyrings/sagernet.asc
    sudo chmod a+r /etc/apt/keyrings/sagernet.asc
    echo "deb [arch=`dpkg --print-architecture` signed-by=/etc/apt/keyrings/sagernet.asc] https://deb.sagernet.org/ * *" | \
      sudo tee /etc/apt/sources.list.d/sagernet.list > /dev/null
    sudo apt-get update
    sudo apt-get install sing-box-beta
)
```

## reference

- [sing-box tproxy - 心底的河流](https://lhy.life/20231012-sing-box-tproxy/)
