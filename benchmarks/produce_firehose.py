import io
import zlib
import os
import hashlib

from atmst.blockstore import MemoryBlockStore
from atmst.mst.node_store import NodeStore
from atmst.mst.node import MSTNode
from atmst.mst.node_wrangler import NodeWrangler
from atmst.mst.diff import mst_diff

from cbrrr import encode_dag_cbor, decode_dag_cbor, CID

from util import tid_now, iso_string_now, enumerate_blobs, CarWriter
from iterate_records import iterate_records

REPO_DID = "did:plc:oky5czdrnfjpqslsw2a5iclo"

FIREHOSE2 = True
COMPRESS = True

if __name__ == "__main__":
	bs = MemoryBlockStore()
	ns = NodeStore(bs)
	wrangler = NodeWrangler(ns)
	prev_mst_root = ns.stored_node(MSTNode.empty_root()).cid

	outfile = open("firehose2.bin" if FIREHOSE2 else "firehose.bin", "wb")

	since = None
	for seq, (path, record) in enumerate(iterate_records("../test_data/jay.bsky.team.car")):
		record_bytes = encode_dag_cbor(record)
		record_cid = CID.cidv1_dag_cbor_sha256_32_from(record_bytes)
		blobs = list(enumerate_blobs(record))

		#print(path, record_cid.encode())
		mst_root = wrangler.put_record(prev_mst_root, path, record_cid)
		created, deleted = mst_diff(ns, prev_mst_root, mst_root)

		rev_tid = tid_now()

		ops_array = [{
			"action": "create",
			"path": path,
			"cid": record_cid
		}]

		commit_object = {
			"did": REPO_DID,
			"version": 4 if FIREHOSE2 else 3,
			"data": mst_root,
			"rev": rev_tid,
			"prev": None,
		} | ({
			"opsCid": CID.cidv1_dag_cbor_sha256_32_from(encode_dag_cbor(ops_array))
		} if FIREHOSE2 else {})

		commit_object["sig"] = hashlib.sha512(encode_dag_cbor(commit_object)).digest() # this isn't a real signature but it should be a decent stand-in approximation (64 bytes of uncompressible data)
		commit_bytes = encode_dag_cbor(commit_object)
		commit_cid = CID.cidv1_dag_cbor_sha256_32_from(commit_bytes)

		car = io.BytesIO()
		car_writer = CarWriter(car, commit_cid)
		car_writer.write_block(commit_cid, commit_bytes)
		for created_cid in created:
			car_writer.write_block(created_cid, bs.get_block(bytes(created_cid)))
		car_writer.write_block(record_cid, record_bytes)

		event = {
			"seq": seq,
			"rebase": False,
			"tooBig": False,
			"repo": REPO_DID,
			"prev": None,
			"rev": rev_tid,
			"since": since,
			"time": iso_string_now() # TODO: consider using unix millis integer? or unix seconds fp64?
		} | ( {
			"commitSig": commit_object["sig"], # don't store the commit object itself, the client should have all the data necessary to reconstruct it
			"ops": [{
				"action": "create",
				"path": path,
				# store the data, not the CID! client can derive CID, assuming sha256/dag-cbor format
				"record": record_bytes # serialised dag-cbor bytes
			}],
			# we don't store the "blobs" array, it should be possible to infer it from the record bodies?
		} if FIREHOSE2 else {
			"commit": commit_cid,
			"blocks": car.getvalue(),
			"blobs": blobs,
			"ops": ops_array,
		})

		event_bytes = encode_dag_cbor(event)
		if COMPRESS:
			event_bytes = zlib.compress(event_bytes, level=9, wbits=-15)
		outfile.write(len(event_bytes).to_bytes(4))
		outfile.write(event_bytes)

		#print(created)
		prev_mst_root = mst_root
		since = rev_tid
	
	outfile.close()
	print("Final mst root:  ", mst_root.encode())
