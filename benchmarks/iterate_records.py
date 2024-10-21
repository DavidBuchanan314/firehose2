# https://github.com/DavidBuchanan314/atmst
from atmst.blockstore.car_file import ReadOnlyCARBlockStore
from atmst.mst.node_store import NodeStore
from atmst.mst.node_walker import NodeWalker

# https://github.com/DavidBuchanan314/dag-cbrrr
from cbrrr import encode_dag_cbor, decode_dag_cbor, CID

from typing import Iterable, Tuple

def iterate_records(car_path: str) -> Iterable[Tuple[str, bytes]]:
	carfile = open(car_path, "rb")
	bs = ReadOnlyCARBlockStore(carfile)
	commit = decode_dag_cbor(bs.get_block(bytes(bs.car_root)))
	mst_root = commit["data"]

	print("Initial mst root:", mst_root.encode())

	# load all records
	records = {}
	for k, v in NodeWalker(NodeStore(bs), mst_root).iter_kv():
		records[k] = decode_dag_cbor(bs.get_block(bytes(v)))

	print(f"{len(records)} records loaded.")

	# iterate in rkey order (chronological, assuming all rkeys are TIDs)
	for path in sorted(records.keys(), key=lambda x: x.split("/")[-1]):
		yield path, records[path]
