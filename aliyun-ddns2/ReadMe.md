### 用途
用于向阿里云DNS服务注册本机获取到的访问公网的地址

### 参考
程序基于"fisherworks.cn"的代码改编(我找不到他的github地址了)

### 说明
有2个文件:ddns_aliyun.py和ddns_aliyun.conf

ddns_aliyun.conf内容

```shell
{
    "RR": "",   #要注册的域名前缀，为空的时候自动获取主机名
    "Type": "aaaa", #域名类型，支持a和aaaa，为空的时候取a,aaaa；分别创建2条解析
    "DOMAIN_NAME": "laohao.ren",    #你自己拥有的在阿里云的域名
    "ACCESS_KEY": "LTaaaaaaaaaaaaaa",   #你自己的阿里云的Key和Secret，分配最小的权限即可
    "ACCESS_SECRET": "xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  }
```
配置文件名默认与执行的py文件名相同，如果不同可以用-c或--config指定
    ./ddna_aliyun.py --config config.conf

### 依赖的库
ipy
requests
aliyun-python-sdk-core
会自动安装一些其他的库


### 基本执行逻辑(暂略)

- 调用_getNewPublicIp从returnip.zanservice.com:8078/ip获取IP地址，可重写该函数
- 提供IP地址的站点，是直接基于nginx的，配置参见returnip.ngx.conf，可自行部署
- 需要创建3个域名解析(如果仅其中2个)到这个IP地址的获取站点。

- 域名如果已经存在可以覆盖现有ip，未创建则会自动创建；
- 不会删除已有的域名解析记录  


### 定时运行
ddns_aliyun.service和ddns_aliyun.timer为linux环境下的服务及定时任务的配置文件，放置在 /usr/lib/systemd/system/ 目录  
使用sudo systemctl enable ddns_aliyun.timer生效，目前的参数配置为启动后20秒执行，然后每180秒执行一次。正常情况每10分钟也可以了。

可执行的ddns_aliyun.py和ddns_aliyun.conf放置在目录/export/script/
由于system的service默认是以root的用户身份运行，因此如果启用定时运行的话，需要注意包的安装，建议使用root身份进行包安装。
没有研究过在服务器端(生产环境)部署python虚拟环境、且在后台启动的方法。






