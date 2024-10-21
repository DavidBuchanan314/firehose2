import zlib

from atmst.blockstore import MemoryBlockStore
from atmst.mst.node_store import NodeStore
from atmst.mst.node import MSTNode
from atmst.mst.node_wrangler import NodeWrangler
from atmst.mst.diff import mst_diff


from cbrrr import encode_dag_cbor, decode_dag_cbor, CID

from crypto import privkey_from_pem, encode_dss_signature, assert_dss_sig_is_low_s, ECDSA_SHA256

if __name__ == "__main__":
	bs = MemoryBlockStore()
	ns = NodeStore(bs)
	wrangler = NodeWrangler(ns)
	prev_mst_root = ns.stored_node(MSTNode.empty_root()).cid

	pubkey = privkey_from_pem(open("privkey.pem").read()).public_key()

	with open("firehose2.bin", "rb") as stream:
		while msg_len := int.from_bytes(stream.read(4)):
			event = decode_dag_cbor(zlib.decompress(stream.read(msg_len), wbits=-15))
			mst_root = prev_mst_root
			reconstructed_ops = []
			for op in event["ops"]:
				# TODO: check that no two ops reference the same path
				if op["action"] in ["create", "update"]:
					record_cid = CID.cidv1_dag_cbor_sha256_32_from(op["record"])
					mst_root = wrangler.put_record(mst_root, op["path"], record_cid)
					reconstructed_ops.append({
						"action": op["action"],
						"path": op["path"],
						"cid": record_cid # TODO: I suppose there's no real need for this, we could just use the existing ops structure
					})
				elif op["action"] == "delete":
					mst_root = wrangler.del_record(mst_root, op["path"])
					reconstructed_ops.append({
						"action": op["action"],
						"path": op["path"]
					})
			
			reconstructed_commit = {
				"did": event["repo"],
				"version": 4,
				"data": mst_root, # NB: someone not doing full sync won't be able to calculate this!!!
				"rev": event["rev"],
				"prev": None,
				"opsCid": CID.cidv1_dag_cbor_sha256_32_from(encode_dag_cbor(reconstructed_ops))
			}

			assert(len(event["commitSig"]) == 64)
			r = int.from_bytes(event["commitSig"][:32])
			s = int.from_bytes(event["commitSig"][32:])
			dss_sig = encode_dss_signature(r, s)
			assert_dss_sig_is_low_s(dss_sig, pubkey.curve)
			pubkey.verify(dss_sig, encode_dag_cbor(reconstructed_commit), ECDSA_SHA256) # nb, this throws an exception on verification failure

			prev_mst_root = mst_root
	
	print("Final MST root:", prev_mst_root.encode())
