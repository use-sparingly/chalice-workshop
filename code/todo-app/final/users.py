import os
import json
import getpass
import argparse
import hashlib
import hmac
import six
import sys

import boto3
from boto3.dynamodb.types import Binary

stdin_encoding = sys.stdin.encoding or 'utf-8'

def get_table_name(stage):
    # We might want to user the chalice modules to
    # load the config.  For now we'll just load it directly.
    with open(os.path.join('.chalice', 'config.json')) as f:
        data = json.load(f)
    return data['stages'][stage]['environment_variables']['USERS_TABLE_NAME']


def create_user(stage):
    table_name = get_table_name(stage)
    table = boto3.resource('dynamodb').Table(table_name)
    username = six.moves.input('Username: ').strip()
    password = getpass.getpass('Password: ').strip()

    if isinstance(username, six.binary_type):
        # Python >=2.x
        # Convert to Unicode using console encoding
        username = username.decode(stdin_encoding)

    if isinstance(password, six.binary_type):
        # Python >=2.x
        # Convert to Unicode using console encoding
        password = password.decode(stdin_encoding)

    password_fields = encode_password(password)
    item = {
        'username': username,
        'hash': password_fields['hash'],
        'salt': Binary(password_fields['salt']),
        'rounds': password_fields['rounds'],
        'hashed': Binary(password_fields['hashed']),
    }
    table.put_item(Item=item)


def encode_password(password, salt=None):
    # Ensure password is Py2:Unicode,Py3:str
    assert isinstance(password, six.text_type)

    if salt is None:
        salt = os.urandom(16)

    # Encode password to UTF-8.
    password_bytes = password.encode("UTF-8")

    rounds = 100000
    hashed = hashlib.pbkdf2_hmac('sha256', password_bytes, salt, rounds)
    return {
        'hash': 'sha256',
        'salt': salt,
        'rounds': rounds,
        'hashed': hashed,
    }


def list_users(stage):
    table_name = get_table_name(stage)
    table = boto3.resource('dynamodb').Table(table_name)
    for item in table.scan()['Items']:
        print(item['username'])


def test_password(stage):
    username = six.moves.input('Username: ').strip()
    password = getpass.getpass('Password: ').strip()

    if isinstance(username, six.binary_type):
        # Python 2.x
        # Convert to Unicode using console encoding
        username = username.decode(stdin_encoding)

    if isinstance(password, six.binary_type):
        # Python 2.x
        # Convert to Unicode using console encoding
        password = password.decode(stdin_encoding)

    table_name = get_table_name(stage)
    table = boto3.resource('dynamodb').Table(table_name)
    item = table.get_item(Key={'username': username})['Item']
    encoded = encode_password(password, salt=item['salt'].value)
    if hmac.compare_digest(encoded['hashed'], item['hashed'].value):
        print("Password verified.")
    else:
        print("Password verification failed.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--create-user', action='store_true')
    parser.add_argument('-t', '--test-password', action='store_true')
    parser.add_argument('-s', '--stage', default='dev')
    parser.add_argument('-l', '--list-users', action='store_true')
    args = parser.parse_args()
    if args.create_user:
        create_user(args.stage)
    elif args.list_users:
        list_users(args.stage)
    elif args.test_password:
        test_password(args.stage)


if __name__ == '__main__':
    main()
