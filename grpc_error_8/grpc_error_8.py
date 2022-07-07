import logging, logging.handlers
import copy
import os
import random
import string
import threading


# leaving this here as a note
# from importlib import reload
# reload(<module>)

from datetime import datetime, timezone

from pprint import pformat
from time import sleep

from typedb.client import (
    TypeDB, 
    TypeDBOptions,
    SessionType, 
    TransactionType,
    Iterator,
    ConceptMap,
    TypeDBClientException,
    QueryFuture,
)

from typing import (
    DefaultDict,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

class Trouble():
    def __init__(
        self
    ):

        self.logger: logging.Logger = logging.getLogger('trouble')
        _log = self.logger
        self.db_server = '127.0.0.1:1729'
        self.db_name = 'troubleshoot_db'
        self.parallelisation = 2
        infer = False
        explain = False
        parallel = True
        prefetch_size = 50
        trace_inference = False
        session_idle_timeout_millis = 30000
        transaction_timeout_millis = 300000
        schema_lock_acquire_timeout_millis = 10000

        self.db_options = self._set_db_options(
            infer=infer,
            explain=explain,
            parallel=parallel,
            prefetch_size=prefetch_size,
            trace_inference=trace_inference,
            session_idle_timeout_millis=session_idle_timeout_millis,
            transaction_timeout_millis=transaction_timeout_millis,
            schema_lock_acquire_timeout_millis=schema_lock_acquire_timeout_millis,
        )

        self._init_logger(
            log_dir="./logs/",
            log_level="INFO",
            log_maxbytes=3000000,
            log_backup_count=5,
            log_syntax='text',
        )
        _log = self.logger

        self.client = None
        self.client = self.create_client()
        self.session = None
        self.tx = None
        self.runner = None

        self.schema = {
            'Relations': [
                {
                    'label': 'hunt',
                    'has': [
                        'hunt-name',
                        'note',
                        'tag',
                        'confidence',
                        'date-seen',
                        'first-seen',
                        'last-seen',
                        'hunt-active',
                        'hunt-endpoint',
                        'hunt-service',
                        'hunt-string',
                        'first-hunted',
                        'last-hunted',
                        'frequency',
                    ],
                }
            ],
            'Entities': [
                {
                    'label': 'hostname',
                    'has': [
                        'hunt-name',
                        'note',
                        'tag',
                        'confidence',
                        'date-seen',
                        'first-seen',
                        'last-seen',
                        'hunt-active'
                    ],
                    'key': 'fqdn',
                },
                {
                    'label': 'ip',
                    'has': [
                        'hunt-name',
                        'note',
                        'tag',
                        'confidence',
                        'date-seen',
                        'first-seen',
                        'last-seen',
                        'hunt-active'
                    ],
                    'key': 'ip-address',
                },
                {
                    'label': 'ssl',
                    'has': [
                        'hunt-name',
                        'note',
                        'tag',
                        'confidence',
                        'date-seen',
                        'first-seen',
                        'last-seen',
                        'sha256',
                        'issued-date',
                        'expires-date',
                        'issuer-c',
                        'issuer-cn',
                        'issuer-o',
                        'issuer-l',
                        'issuer-st',
                        'issuer-ou',
                        'pubkey-bits',
                        'pubkey-type',
                        'sig-alg',
                        'version',
                        'subject-c',
                        'subject-cn',
                        'subject-o',
                        'subject-l',
                        'subject-st',
                        'subject-ou',
                        'cipher-bits',
                        'cipher-name',
                        'ja3s',
                        
                    ],
                    'key': 'fingerprint',
                },
                {
                    'label': 'jarm',
                    'has': [
                        'hunt-name',
                        'note',
                        'tag',
                        'confidence',
                        'date-seen',
                        'first-seen',
                        'last-seen',
                        'jarm-cipher',
                        'jarm-tls-ext',
                    ],
                    'key': 'fingerprint',
                },
            ],
            'Attributes': {
                'cipher-bits': 'string',
                'cipher-name': 'string',
                'confidence': 'double',
                'date-seen': 'datetime',
                'expires-date': 'datetime',
                'fingerprint': 'string',
                'first-hunted': 'datetime',
                'first-seen': 'datetime',
                'fqdn': 'string',
                'frequency': 'double',
                'hunt-active': 'boolean',
                'hunt-endpoint': 'string',
                'hunt-name': 'string',
                'hunt-service': 'string',
                'hunt-string': 'string',
                'ip-address': 'string',
                'issued-date': 'datetime',
                'issuer-c': 'string',
                'issuer-cn': 'string',
                'issuer-o': 'string',
                'issuer-l': 'string',
                'issuer-st': 'string',
                'issuer-ou': 'string',
                'ja3s': 'string',
                'jarm-cipher': 'string',
                'jarm-tls-ext': 'string',
                'last-hunted': 'datetime',
                'last-seen': 'datetime',
                'note': 'string',
                'pubkey-bits': 'double',
                'pubkey-type': 'string',
                'sha256': 'string',
                'sig-alg': 'string',
                'subject-c': 'string',
                'subject-cn': 'string',
                'subject-o': 'string',
                'subject-l': 'string',
                'subject-st': 'string',
                'subject-ou': 'string',
                'tag': 'string',
                'version': 'string',
            },
        }

    def _init_logger(
        self,
        log_dir,
        log_level,
        log_maxbytes,
        log_backup_count,
        log_syntax
    ) -> None:

        self.logger.setLevel(log_level.upper())
        self.logger.handlers=[]
        formatter = logging.Formatter
        stderr_handler = logging.StreamHandler()
        stderr_logformat = formatter(
            u"%(asctime)s [%(levelname)s] %(name)s > "
            u"%(filename)s > (%(funcName)s) [%(lineno)d] > "
            u" %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        stderr_handler.setFormatter(stderr_logformat)
        self.logger.addHandler(stderr_handler)

        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            log_file = f"trouble.log"
            log_path = os.path.abspath(
                os.path.join(log_dir, log_file)
            )
            rfh  = logging.handlers.RotatingFileHandler
            file_handler = rfh(
                filename=log_path,
                mode='a',
                maxBytes=log_maxbytes,
                backupCount=log_backup_count,
                encoding= 'UTF-8',
            )
            file_logformat = formatter(
                u"%(asctime)s [%(levelname)s] %(name)s > "
                u"%(filename)s > (%(funcName)s) [%(lineno)d] > "
                u" %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_logformat)
            self.logger.addHandler(file_handler)
            self.logger.debug(f"Writing logs to {log_path}...")

    def _set_db_options(
        self,
        **kwargs
    ):
        _log = self.logger
        options = TypeDBOptions.core()
        options.__dict__.update(kwargs)
        _log.info(f"{pformat(options)}")
        return options

    def create_client(
        self,
        db_server: Optional[str] = '',
        threads: Optional[str] = '',
    ):
        _log = self.logger
        db_server = db_server or self.db_server
        threads = threads or self.parallelisation
        client = TypeDB.core_client(db_server, threads)
        if not self.client:
            self.client = client
        _log.info(f"Created DB Client for {db_server} with {threads} threads!")
        return client

    def create_session(
        self,
        session_type: Optional[SessionType] = SessionType.DATA, 
        client: Optional[TypeDB.core_client] = None, 
        db_name: Optional[str] = '',
        options: Optional[TypeDBOptions.core] = None,
    ):
        _log = self.logger
        client = client or self.client
        if not client:
            client = self.create_client()

        db_name = db_name or self.db_name
        session = client.session(db_name, session_type, options)
        _log.info(f"Opened session to {db_name}.")
        return session

    def create_tx(
        self,
        db_name: Optional[str] = "",
        tx_type: Optional[TransactionType] = TransactionType.READ,
        client: Optional[TypeDB.core_client] = None,
        session: Optional[object] = None,
        session_type: Optional[SessionType] = SessionType.DATA,
        options: Optional[TypeDBOptions.core] = None,
    ):
        _log = self.logger

        if not db_name:
            db_name = self.db_name
        if not db_name:
            _log.error(f"db_name required, but none received.")
            return False
        client = client or self.client
        if not client:
            client = self.create_client()
        if not session:
            session = self.create_session(
                session_type=session_type,
                client=client,
                db_name=db_name,
                options=options,
            )
        tx = session.transaction(tx_type, options)
        _log.info(f"Opened {tx_type} to {db_name} with {session.session_type()}.")
        return tx, session

    def check_db(
        self,
        db_name: str = "",
        client: Optional[TypeDB.core_client] = None, 
    ):
        client = client or self.client
        exists = client.databases().contains(db_name)
        return exists

    def create_db(
        self,
        db_name: Optional[str] = "",
        client: Optional[TypeDB.core_client] = None,
    ):
        _log = self.logger
        client = client or self.client
        db_name = db_name or self.db_name
        client.databases().create(db_name)
        _log.debug(f"Created {db_name}!")
        return True

    def delete_db(
        self,
        db_name: str = "",
        client: Optional[TypeDB.core_client] = None, 
    ):
        _log = self.logger
        _log.info(f"Deleting {db_name}...")
        client = client or self.client
        db_name = db_name or self.db_name
        exists = self.check_db(db_name)
        if not exists:
            return True
        client.databases().get(db_name).delete()
        return True

    def fake_data(
        self,
        data_type: Optional[str] = 'string',
        max_length: Optional[int] = 15,
    ):
        _log = self.logger

        if data_type=='string':
            slen = random.randint(4, max_length)
            s = ''.join(random.choices(string.ascii_lowercase, k=slen))
        elif data_type=='double':
            s = random.randint(0,10)
        elif data_type=='datetime':
            epoch = random.randint(1,1893459600)
            sdt = datetime.fromtimestamp(epoch)
            sdt = sdt.replace(tzinfo=timezone.utc)
            # s = sdt.strftime("%Y-%m-%dT%H:%M:%S")
            s = sdt
        elif data_type=='boolean':
            s = random.choices([True,False])[0]
        return s

    def gen_attrs(
        self,
        attr_count: int = 1,
        choices: Optional[List] = None,
    ):
        _log = self.logger
        if not choices:
            choices = list(self.schema['Attributes'].keys())
        attrs = []
        for a in range(attr_count):
            a_select = random.choices(choices)[0]
            label = a_select
            dtype = self.schema['Attributes'][label]
            value = self.fake_data(data_type=dtype)
            attr = {
                'label': label,
                'value': value,
            }
            attrs.append(attr)
        return attrs

    def gen_entities(
        self,
        ent_count: int = 3,
        attr_count: int = 3,
    ):
        _log = self.logger
        all_ents = []
        for e in range(ent_count):
            ent_select = random.choices(self.schema['Entities'])[0]
            ent = {
                'label': ent_select['label'],
                'has': [],
                'keyattr': None,
            }
            attr_choices = ent_select['has']
            has = self.gen_attrs(
                attr_count=attr_count,
                choices=attr_choices,
            )
            ent['has']=has
            if ent_select['key']:
                attr_choices = [ent_select['key']]
                key_attr = self.gen_attrs(
                    attr_count=1,
                    choices=attr_choices,
                )
                ent['has'].append(key_attr[0])
                ent['keyattr'] = key_attr[0]
            all_ents.append(ent)
        return all_ents

    def gen_relations(
        self,
        rel_count: int = 1,
        attr_per_rel: int = 1,
        players_per_rel: int = 3,
    ):
        _log = self.logger
        all_rels = []
        for r in range(rel_count):
            rel = {
                'label': 'hunt',
                'has': [],
                'players': {'found': []},
            }
            # Generate Attributes
            choices = self.schema['Relations'][0]['has']
            rel['has'] = self.gen_attrs(
                attr_per_rel,
                choices,
            )
            # Generate Players/Entities
            rel['players']['found'] = self.gen_entities(
                ent_count=players_per_rel,
                attr_count=3,
            )
            all_rels.append(rel)
        return all_rels

    def gen_data(
        self,
        db_name: str = '',
        total_rels: int = 1,
        attr_per_rel: int = 1,
        players_per_rel: int=3,
    ):
        _log = self.logger
        

        all_rels = self.gen_relations(
            rel_count = total_rels,
            attr_per_rel = attr_per_rel,
            players_per_rel = players_per_rel,
        )

        self.write_things(
            db_name=db_name,
            relations=all_rels,
        )


        # self.gen_relation()
        _log.info(f"Data generated.")

    def populate_db(
        self,
        db_name: str = '',
        total_rels: int = 50,
        attr_per_rel: int = 3,
        players_per_rel: int = 3,
    ):
        _log = self.logger
        if not db_name:
            db_name = self.db_name
        if not db_name:
            _log.error(f"db_name required!")
            return False
        # Delete DB
        self.delete_db(db_name)
        # Create DB
        self.create_db(db_name)
        # Write Schema
        self.write_tql_file(file='schema.tql')
        # Generate & Populate Data
        self.gen_data(
            total_rels= total_rels,
            attr_per_rel= attr_per_rel,
            players_per_rel=players_per_rel,
        )

        _log.info(f"Database {db_name} successfully generated and popoulated with dummy data.")

    def write_things(
        self,
        db_name: str = '',
        relations: list = [],
        # entities: list = [],
        # attributes: list = [],
    ):
        _log = self.logger
        tx, session = self.create_tx(
            tx_type=TransactionType.WRITE,
        )

        all_attrs = []
        all_ents = []
        unique_ents = []
        for rel in relations:
            for h in rel['has']:
                if h not in all_attrs:
                    all_attrs.append(h)
            for e in rel['players']['found']:
                if e['keyattr']:
                    if e['keyattr'] not in unique_ents:
                        unique_ents.append(e['keyattr'])
                        all_ents.append(e)
                else:
                    all_ents.append(e)

        # Write the entities first
        for ent in all_ents:
            q = f"insert $x isa {ent['label']}"
            for h in ent['has']:
                val = h['value']
                if isinstance(val, datetime):
                    val = val.strftime("%Y-%m-%dT%H:%M:%S")
                elif isinstance(val, str):
                    val = f'"{val}"'
                elif isinstance(val, bool):
                    val = str(val).lower()
                elif isinstance(val, int):
                    val = round(float(val),2)
                elif isinstance(val, float):
                    val = round(float(val),2)
                q += f", has {h['label']} {val}"
            q += ";"
            _log.info(f"Inserting Entity:")
            _log.info(q)
            tx.query().insert(q)
        # tx.commit()

        # Then write the relations
        rel_count = 0
        for rel in relations:
            ent_count = 0
            ent_vars = []
            q = f"match "
            for ent in rel['players']['found']:
                ent_var = ent['label']+str(ent_count)
                ent_vars.append(ent_var)
                q += f"${ent_var} isa {ent['label']}"

                for h in ent['has']:
                    val = h['value']
                    if isinstance(val, datetime):
                        val = val.strftime("%Y-%m-%dT%H:%M:%S")
                    elif isinstance(val, str):
                        val = f'"{val}"'
                    elif isinstance(val, bool):
                        val = str(val).lower()
                    elif isinstance(val, int):
                        val = round(float(val),2)
                    elif isinstance(val, float):
                        val = round(float(val),2)
                    q += f", has {h['label']} {val}"
                q += "; "
                ent_count += 1
            rel_var = rel['label']+str(rel_count)
            q += f"insert ${rel_var} ("
            for ev in ent_vars:
                q += f"found: ${ev},"
            q = q.rstrip(',')
            q += f") isa {rel['label']};"

            for h in rel['has']:
                val = h['value']
                if isinstance(val, datetime):
                    val = val.strftime("%Y-%m-%dT%H:%M:%S")
                elif isinstance(val, str):
                    val = f'"{val}"'
                elif isinstance(val, bool):
                    val = str(val).lower()
                elif isinstance(val, int):
                    val = round(float(val),2)
                elif isinstance(val, float):
                    val = round(float(val),2)
                q += f" ${rel_var} has {h['label']} {val};"
            # q += ";"
            _log.info(f"Inserting Relation:")
            _log.info(q)
            tx.query().insert(q)
            rel_count+=1

        tx.commit()
        session.close()
        return True

    def write_tql_file(
        self,
        file: str = 'schema.tql',
        is_schema: Optional[bool] = True,
        client: Optional[TypeDB.core_client] = None,
        db_name: Optional[str] = '',
        options: Optional[TypeDBOptions] = None,
    ):
        """
        Writes schema file to database.

        :param is_schema: True if writing a SCHEMA. False if writing a RULE.
        """
        _log = self.logger
        client = client or self.client
        db_name = db_name or self.db_name

        if is_schema:
            session_type = SessionType.SCHEMA
        else:
            session_type = SessionType.DATA

        db_exists = self.check_db(db_name)
        if not db_exists:
            _log.error(
                f"Database {db_name} does not exist. Cannot write schema!"
            )
            return False

        tql = ""
        with open(file, 'r') as f:
            for line in f.readlines():
                tql+=line
        _log.info(f"Writing TQL file {file}...")

        with client.session(db_name, session_type) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                try:
                    tx.query().define(tql)
                    tx.commit()

                except Exception:
                    _log.error("Exception writing schema!", exc_info=True)
                    tx.close()
                    session.close()
                    raise

        return True

    # Test_three functions
    def churn_concept(
        self,
        concept,
        tx,
    ):
        _log=self.logger
        if concept.is_thing():
            concept_type = concept.get_type()
        elif concept.is_type():
            concept_type = concept
        # print(f"Answer is {concept_type}")
        label = concept_type.get_label().name()
        if not concept_type.is_role_type():
            iid = concept.get_iid()
            inferred = concept.is_inferred()

        value = None
        if concept_type.is_attribute_type():
            if concept.is_thing():
                value = concept.get_value()
            elif concept.is_type():
                value = ''

        elif concept_type.is_entity_type():
            value = "entity"

        elif concept_type.is_relation_type():
            value = "relation"

        elif concept_type.is_role_type():
            value = 'role'

        has = None
        rels = None
        if value=='entity':
            remote_concept = concept.as_remote(tx)
            has = remote_concept.get_has()
            for h in has:
                self.churn_concept(h, tx)
            rels = remote_concept.get_relations()
            for rel in rels:
                rel_type = rel.get_type()
                rel_type.get_label().name()
                rel.get_iid()
                rel.is_inferred()
                rel_has = rel.as_remote(tx).get_has()
                for rh in rel_has:
                    self.churn_concept(rh, tx)

        elif value=='role':
            remote_concept = concept.as_remote(tx)
            concept_type.get_label().scope()
            concept_type.get_label().scoped_name()

        elif value=='relation':
            remote_concept = concept.as_remote(tx)
            has = remote_concept.get_has()
            for h in has:
                self.churn_concept(h, tx)

            players = remote_concept.get_players_by_role_type()
            for role_concept, ent_concepts in players.items():
                self.churn_concept(role_concept, tx)
                for ent_concept in ent_concepts:
                    self.churn_concept(ent_concept, tx)

        return True

    def churn(
        self,
        tx: object = None,
        q: str = '',
        var: str = '',
    ):
        _log = self.logger

        answers = tx.query().match(q)
        for answer in answers:
            concepts = answer.concepts()
            for concept in concepts:
                self.churn_concept(concept, tx)

    def test_three(
        self,
    ):
        _log = self.logger

        self.populate_db(
            total_rels=10,
            attr_per_rel=5,
        )

        # Reproduce issues here

        tx, session = self.create_tx()
        q1 = "match $hunt($found) isa hunt, has hunt-string $hs, has attribute $hattr;"
        var1 ="hs"
        q2 = "match $hunt($found) isa hunt, has hunt-endpoint $he, has attribute $hattr;"
        var2 = "he"

        # Churn results simultaneously
        # Set up threads
        thread1 = threading.Thread(target=self.churn, args=(tx, q1, var1))
        thread2 = threading.Thread(target=self.churn, args=(tx, q2, var2))

        # Call first search and while first search is processing, call a second
        _log.info(f"Starting test_three...")
        _log.info(f"Starting Thread1")
        thread1.start()
        _log.info(f"Starting Thread2")
        thread2.start()
        _log.info(f"Done test_three!")


if __name__=="__main__":

    # Populate a dummy database
    t = Trouble()
    t.test_three()
