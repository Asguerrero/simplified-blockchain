# This is a simplified model of a blockchain that works as a cryptocurrency

# To be installed:
# Flask==0.12.2: pip install Flask==0.12.2
# requests==2.18.4: pip install requests==2.18.4

# Importing the libraries
import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse

# Part 1 - Building a Blockchain

class Blockchain:

    def __init__(self):
        self.chain = []
        self.transactions = []
        genesis_block = self.create_new_block(previous_hash = '0')
        genesis_block_with_nounce = self.get_nounce(genesis_block)
        self.insert_block(genesis_block_with_nounce)
        self.nodes = set()
        
    def create_new_block(self, previous_hash):
        block = {'index': len(self.chain) + 1,
                 'timestamp': str(datetime.datetime.now()),
                 'previous_hash': previous_hash,
                 'nounce': '',
                 'current_hash': '',
                 'transactions': self.transactions}
        self.transactions = []
        return block
    
        
    def get_nounce(self, block):
        nounce = 1
        check_nounce = False
        while check_nounce is False:
            block['nounce'] = nounce
            hash_operation = hashlib.sha256(str(block).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_nounce = True
                block['current_hash'] = hash_operation
            else:
                nounce += 1   
        return block
                   
        
    def insert_block(self, block):
        self.chain.append(block)
        return block
        
    

    def get_previous_block(self):
        return self.chain[-1]

    
    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            block_without_current_hash ={
                'index': block['index'],
                 'timestamp': block['timestamp'],
                 'previous_hash': block['previous_hash'],
                 'nounce': block['nounce'],
                 'current_hash': '',
                 'transactions': block['transactions']
            }
            hash_operation = hashlib.sha256(str(block_without_current_hash).encode()).hexdigest()
            if block['previous_hash'] != previous_block['current_hash']:
                return False
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
        return True

    def add_transaction(self, sender, receiver, amount):
        transaction = {
            "sender" : sender,
            "receiver" : receiver,
            "amount" : amount,
            "timestamp": str(datetime.datetime.now()),
            "hash": ''
            }
        hash_operation = self.get_transaction_hash(transaction)
        transaction['hash']= hash_operation
        self.transactions.append(transaction)
        previous_block = self.get_previous_block()
        return previous_block['index'] + 1

    def get_transaction_hash(self, transaction):
        hash_operation = hashlib.sha256(str(transaction).encode()).hexdigest()
        return hash_operation
        

    def add_node(self, address):
            parsed_url = urlparse(address)
            self.nodes.add(parsed_url.netloc)   
    
    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length:
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        return False

    def get_mempools(self):
        network = self.nodes
        others_transactions =[]
        for node in network:
            response = requests.get(f'http://{node}/get_mempool')
            if response.status_code == 200:
                transactions = response.json()['transactions']
                if transactions:
                    for transaction in transactions:
                        others_transactions.append(transaction)
                    return others_transactions   


    def find_new_transactions(self, others_transactions):
        if others_transactions:
            new_transactions = []
            for transaction in others_transactions:
                if transaction not in self.transactions:
                    new_transactions.append(transaction)

            return new_transactions


    def update_mempool(self, new_transactions):
        if new_transactions:
            for transaction in new_transactions:
                self.transactions.append(transaction)
            return True
        else:
            return False

    def duplicated_transactions(self):
        blockchain = self.chain
        duplicated = False
        for block in blockchain:
            for transaction in block['transactions']:
                if transaction in self.transactions:
                    self.transactions.remove(transaction)
                    duplicated = True
                
        return duplicated


# Part 2 - Implementing the Blockchain

# Creating a Web App
app = Flask(__name__)

# Creating an address for the node on Port 5000
node_address = str(uuid4()).replace('-', '')

# Creating a Blockchain
blockchain = Blockchain()


# Main requests meant to be used by users

# Connecting to the other nodes of the network
@app.route('/connect_node', methods = ['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    if nodes is None:
        return "No node", 400
    for node in nodes:
        blockchain.add_node(node)
    response = {'message': 'All the nodes are now connected. The Hadcoin Blockchain now contains the following nodes:',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201


# Mining a new block
@app.route('/mine_block', methods = ['GET'])
def mine_block():
    previous_hash = blockchain.get_previous_block()['current_hash']
    raw_new_block = blockchain.create_new_block(previous_hash)
    new_block = blockchain.get_nounce(raw_new_block)
    inserted_block = blockchain.insert_block(new_block)
    
    response = {'message': 'Congratulations, you just mined a block!',
                'index': inserted_block['index'],
                'timestamp': inserted_block['timestamp'],
                'transactions':inserted_block['transactions'],
                'nounce': inserted_block['nounce'],
                'previous_hash': inserted_block['previous_hash'],
                'current_hash': inserted_block['current_hash']
                }
    return jsonify(response), 200


# Adding a new transaction
@app.route('/add_transaction', methods = ['POST'])
def add_transaction():
    json = request.get_json()
    transaction_keys = ['sender', 'receiver', 'amount']
    if not all(key in json for key in transaction_keys):
        return 'Some elements of the transaction are missing', 400
    index = blockchain.add_transaction(json['sender'], json['receiver'], json['amount'])
    response = {'message': f'This transaction will be added to Block {index}'}
    return jsonify(response), 201


# Getting the most updated version of the blockchain
@app.route('/updated_chain', methods = ['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced == True:
        response = {'message': 'The nodes had different chains so the chain was replaced by the longest one.',
                    'chain': blockchain.chain}
    else:
        response = {'message': 'All good. The chain is the largest one.',
                    'chain': blockchain.chain}
    return jsonify(response), 200


# Getting the most updated version of the mempool
@app.route('/updated_mempool', methods = ['GET'])
def get_updated_mempool():
    new_transactions = blockchain.find_new_transactions(blockchain.get_mempools())
    is_mempool_updated = blockchain.update_mempool(new_transactions)
    duplicated_transactions = blockchain.duplicated_transactions()
    if is_mempool_updated:
        response = {
                'message': "Mempool was updated",
                'duplicated transactions': duplicated_transactions,
                'new_mempool': blockchain.transactions
                }
    else:
        response = {
                'message': "Mempool was not updated",
                'duplicated transactions': duplicated_transactions,
                'new_mempool': blockchain.transactions
                }
    return jsonify(response), 200


# Other methods 

# Getting the full Blockchain (this won't necesarily be the most updated version)
@app.route('/get_chain', methods = ['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200


# Checking if the Blockchain is valid
@app.route('/is_valid', methods = ['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message': 'All good. The Blockchain is valid.'}
    else:
        response = {'message': 'The Blockchain is not valid.'}
    return jsonify(response), 200


# Getting mempool (this won't necesarily be the most updated version)
@app.route('/get_mempool', methods = ['GET'])
def get_mempool():
    response = {'transactions': blockchain.transactions
                }
    return jsonify(response), 200

# Running the app
if __name__ == '__main__':
      app.run(host='0.0.0.0')

