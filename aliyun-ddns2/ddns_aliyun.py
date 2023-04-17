#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
__author__ = "fisherworks.cn"

import sys,getopt,socket,IPy,tempfile
import os, requests, json, logging, logging.handlers
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

#此部分为yaohai增加的

def GetRecType(PubIPAddress ):

    #根据获得的公网IP地址是V4还是V6，决定域名解析的类型是A或者AAAA
    #暂未支持异常判断

    IPVersion=IPy.IP(PubIPAddress).version()

    if IPVersion==4 :
        return("a")
    elif IPVersion==6:
        return("aaaa")
    

def GetConfFile(argv):
    
    HelpMessage="""
    GetPubIP.py -c <Configfile.conf>
    config file example:

    {
    "RR": "aabbcc",
    "Type": "a,aaaa",
    "DOMAIN_NAME": "laohao.ren",
    "ACCESS_KEY": "LTaaaaaaaaaaaaaa",
    "ACCESS_SECRET": "xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
    """

    #print(argv[0])
    ConfFile=os.path.splitext(argv[0])[0]+".conf"
    try:
      opts, args = getopt.getopt(argv[1:],"h:c:",["help","config="])
    except getopt.GetoptError:
      print(HelpMessage)
      sys.exit(2)
    
    for opt ,arg in(opts):
        if opt== "h":
            print(HelpMessage)
            sys.exit()
        elif opt in("-c","--config"):
            ConfFile=arg

    return(ConfFile)


#以上由yaohai增加

def loggerGenerator(loggerName, fileName=None):
    # Set up a specific logger with our desired output level
    logger = logging.getLogger(loggerName)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] %(message)s')
    handler = logging.handlers.RotatingFileHandler(fileName if fileName else os.path.join(tempfile.gettempdir(),loggerName+'.log'),
                                                   maxBytes=2097152, backupCount=5)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('[%(asctime)s] %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logger.addHandler(console)

    return logger


class DdnsClient(object):
    """
    ddns client of Aliyun domain service
    """
    def __init__(self, rr, type,domain, accKey, accSec, logger=None):
        self.logger = logger if logger else loggerGenerator('ddns_client')
        self.rr = rr
        self.type = type
        self.domain = domain
        self.accKey = accKey
        self.accSec = accSec
        self.recordId = ''
        #self.ipRecord = self._getCurrentIpRecord()
    

    def _getNewPublicIp(self,type=''):
        url = "http://returnip.zanservice.com:8078/ip"
        urlv4 = "http://returnipv4.zanservice.com:8078/ip"
        urlv6 = "http://returnipv6.zanservice.com:8078/ip"
        
        if type=='a':
            url=urlv4
        elif type =='aaaa':
            url=urlv6


        try:
            response = requests.request("GET", url, timeout=5)
        except Exception as err:
            self.logger.error('Error - http request error of getLocalPublicIp - {}'.format(err))
            raise RuntimeError(err)

        currentIP=response.text
        
        #print(response)
        return(currentIP)

        if response.status_code != 200:
            self.logger.error('Error - http request error of getLocalPublicIp not 200')
            raise RuntimeError('Error - http request error of getLocalPublicIp not 200')


    def _getCurrentIpRecord(self):
        """
        if you ever set domain record of the RR in this config
        then this method finds and returns the record id and corresponding ip from Aliyun API
        OR if not
        then this method returns blank string
        :return: ip record of this RR.DOMAIN, or blank string
        """
        client = AcsClient(self.accKey, self.accSec, 'default')
        request = CommonRequest()
        request.set_accept_format('json')
        request.set_domain('alidns.aliyuncs.com')
        request.set_method('POST')
        request.set_protocol_type('https')  # https | http
        request.set_version('2015-01-09')
        request.set_action_name('DescribeDomainRecords')
        request.add_query_param('DomainName', self.domain)
        request.add_query_param('TypeKeyWord', self.type)
        
        try:
            response = client.do_action_with_exception(request)
            records = json.loads(response).get('DomainRecords', {}).get('Record', [])
        except Exception as err:
            self.logger.error('Error - aliyun core sdk error of getIpRecord - {}'.format(err))
            raise RuntimeError(err)
        record = next((r for r in records if r.get('RR', '') == self.rr), None)
        if not record:
            self.logger.info('Aliyun ip record with type {} NOT FOUND, need to set the new one'.format(self.type))
            self.ipRecord = ''
            return self.ipRecord
            # raise RuntimeError('Error - getIpRecord nothing - rr not there?')
        # print record
        self.recordId = record.get('RecordId', '')
        self.ipRecord = record.get('Value', '')
        self.logger.info('Aliyun ip record of {}.{} type {} found - {}'.format(self.rr, self.domain,self.type, self.ipRecord))
        return self.ipRecord

    def _addIpRecord(self, rr, newIp,type):
        """
        if this rr was never been set, now we set it (for the 1st time) with the ip
        :param rr: the rr
        :param newIp: the ip
        :return: response from Aliyun API
        """
        client = AcsClient(self.accKey, self.accSec, 'default')
        request = CommonRequest()
        request.set_accept_format('json')
        request.set_domain('alidns.aliyuncs.com')
        request.set_method('POST')
        request.set_protocol_type('https')  # https | http
        request.set_version('2015-01-09')
        request.set_action_name('AddDomainRecord')

        request.add_query_param('DomainName', self.domain)
        request.add_query_param('RR', rr)
        request.add_query_param('Type', type)
        request.add_query_param('Value', newIp)

        
        try:
            response = client.do_action_with_exception(request)
        except Exception as err:
            self.logger.error('Error - aliyun core sdk error of addIpRecord - {}'.format(err))
            raise RuntimeError(err)

        self.logger.info('Aliyun ip record set done - {}'.format(response))
        return response

    def _setNewIpRecord(self, recordId, rr, newIp,type):
        """
        if this rr is already in the Aliyun domain record, now we set that with the new IP
        :param recordId: the record id returned from aliyun
        :param rr: the rr
        :param newIp: the ip
        :return: response from Aliyun API
        """
        client = AcsClient(self.accKey, self.accSec, 'default')
        request = CommonRequest()
        request.set_accept_format('json')
        request.set_domain('alidns.aliyuncs.com')
        request.set_method('POST')
        request.set_protocol_type('https')  # https | http
        request.set_version('2015-01-09')
        request.set_action_name('UpdateDomainRecord')

        request.add_query_param('RecordId', recordId)
        request.add_query_param('RR', rr)
        request.add_query_param('Type', type)
        request.add_query_param('Value', newIp)
        try:
            response = client.do_action_with_exception(request)
        except Exception as err:
            self.logger.error('Error - aliyun core sdk error of setNewIpRecord - {}'.format(err))
            raise RuntimeError(err)

        self.logger.info('Aliyun ip record set done - {}'.format(response))
        return response

    def updateRecord(self):
        """
        let's do it.
        :return: nothing
        """
        newIp = self._getNewPublicIp(self.type)

        newIp_type=GetRecType(newIp)
        """
        判断获取到的ip地址是否与指定的类型相匹配
        还不对，受限应根据指定的类型，获取IP地址
        """
        if self.type :
            if newIp_type != self.type:
                self.logger.error('IP address\' type can not match with conf file.'  )
                return 
        else:
            self.type= newIp_type     


        self.ipRecord = self._getCurrentIpRecord()

        if not self.recordId:
            res = self._addIpRecord(self.rr, newIp,self.type)
        elif newIp == self.ipRecord:
            self.logger.info('same ip - done exit')
        else:
            res = self._setNewIpRecord(self.recordId, self.rr, newIp,self.type)
            self.logger.info('done updated - exit')
        return


if __name__ == "__main__":
    logger = loggerGenerator('ddns_client')
    configfile=GetConfFile(sys.argv)    #修改了config文件的获取方式

    try:
        with open(configfile, 'r') as fp:
            config = json.load(fp)
    except Exception as err:
        logger.error('config file error - {}'.format(err))
        raise IOError('config file error - {}'.format(err))
    # validate the config file
    rr = config.get('RR', '')
    if not rr :
        rr=socket.gethostname()
    rr=rr.lower()
    
    types= config.get('Type','').lower()

    if not types:
        types="a,aaaa"

    types=tuple(types.split(','))

    domain = config.get('DOMAIN_NAME', '')
    key = config.get('ACCESS_KEY', '')
    secret = config.get('ACCESS_SECRET', '')


    if not (rr and domain and key and secret):
        logger.error('config file error - RR, DOMAIN_NAME, ACCESS_KEY and ACCESS_SECRET are all required')
        raise KeyError('config file error - RR, DOMAIN_NAME, ACCESS_KEY and ACCESS_SECRET are all required')
    # validate done, do the update
    for type in types:
        nc = DdnsClient(rr=rr, type=type,domain=domain, accKey=key, accSec=secret, logger=logger)
        nc.updateRecord()
 
    exit(0)

