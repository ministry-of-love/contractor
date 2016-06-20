from errbot import BotPlugin, botcmd, arg_botcmd, webhook

import evelink.api

class Contractor(BotPlugin):
    """
    hack the planet
    """
    
    def do_contract_update(self):
        self.log.info('CONTRACT UPDATING WILL GO HERE')

    def activate(self):
        """
        Triggers on plugin activation
        """
        self.log.info('Activating Contractor Plugin.')
        
        super(Contractor, self).activate()
        if not "API_KEYS" in self:
            self["API_KEYS"] = {}
        if not "CONTRACTS" in self:
            self["CONTRACTS"] = {}
        self.log.info('Starting contract poller.')
        
        self.start_poller(15*60, self.do_contract_update)
    
    @arg_botcmd('v_code', type=str)
    @arg_botcmd('key_id', type=int)
    def api_add(self, message, key_id, v_code):
        """Add an api key to the contractor bot."""
        return self.add_api_key(key_id, v_code)
    
    @botcmd
    def api_list(self, message, args):
        api_keys = self["API_KEYS"]
        yield "The following keys are being watched:"
        for key_id in api_keys:
            yield key_id

    @arg_botcmd('key_id', type=int)
    def api_del(self, message, key_id):
        api_keys = self["API_KEYS"]
        if key_id in api_keys:
            del api_keys[key_id]
            self["API_KEYS"] = api_keys
            return "Removed key with id {0}".format(key_id)
        else:
            return "There is no such key with id {0}".format(key_id)
    
    def add_api_key(self, key_id, v_code):
        api_keys = self["API_KEYS"]
        if key_id in api_keys:
            return "The key with id {0} is already saved".format(key_id)
        else:
            api = evelink.api.API(api_key=(key_id, v_code))
            request = evelink.account.Account(api=api).key_info()
            result = request.result
            type = result['type']
            
            api_keys[key_id] = dict(key=(key_id, v_code), type=type)
            self["API_KEYS"] = api_keys
            self.log.info("Saved API key with id {0}.".format(key_id))
            # self.refresh_contracts_for_api(api_keys])
            if type == 'char' or type == 'account':
                characters = []
                for character_id, character_info in result['characters'].items():
                    characters.append(character_info['name'])
                names = ", ".join(characters)
                return "Added {} key (characters: {}) with id {} and expiry {}".format(result['type'], names, key_id, result['expire_ts'])
            else:
                return "Added {} key with id {} and expiry {}".format(result['type'], key_id, result['expire_ts'])
    
    def refresh_contracts_for_api(self, api_info):
        saved_contracts = self["CONTRACTS"]
        api = evelink.api.API(api_key=api_info['key'])
        
        self.log.info("Refreshing api key ({!s}, {})", api_info['key'][0], api_info['key'][1])
        key_info = evelink.account.Account(api=api).key_info().result
        
        for character_id in key_info['characters']:
            char = evelink.char.Char(char_id=character_id, api=api)
            contracts_result = char.contracts().result
            
            for contract_id, contract_info in contracts_result.items():
                self.log.info("Contract {!s}: {}".format(contract_id, contract_info))
                if contract_id in saved_contracts:
                    prev_contract_info = saved_contracts[contract_id]
                    if prev_contract_info['status'] != contract_info['status']:
                        self.log.info("Contract {0!s} changed state from {} to {}".format(contract_id, prev_contract_info['status'], contract_info['status']))
                        saved_contracts[contract_id] = contracts_info
                        self["CONTRACTS"] = saved_contracts
                elif contract_info['status'] == 'Outstanding':
                    self.log.info("New contract {!s} discovered.".format(contract_id))
                    saved_contracts[contract_id] = contract_info
                    self["CONTRACTS"] = saved_contracts
