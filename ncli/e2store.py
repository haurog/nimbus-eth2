import sys, struct

def read_entry(f):
  header = f.read(8)
  if not header: return (None, None)

  typ = header[0:2] # 2 bytes of type
  dlen = struct.unpack("<I", header[2:6])[0] # 4 bytes of unsigned little-endian length

  data = f.read(dlen)

  return (typ, data)

def read_slot_index(f):
  # Read a slot index, assuming `f` is positioned at the end of the record
  record_end = f.tell()
  f.seek(-8, 1) # Relative seek to get count

  count = struct.unpack("<q", f.read(8))[0]

  record_start = record_end - (8 * count + 24)
  if record_start < 0:
    raise RuntimeError("Record count out of bounds")

  f.seek(record_start) # Absolute seek

  (typ, data) = read_entry(f)

  if typ != b"i2":
    raise RuntimeError("this is not an e2store index record")

  start_slot = struct.unpack("<q", data[0:8])[0]

  # Convert slot indices to absolute file offsets
  slot_entries = (data[(i+1) * 8:(i+2)*8] for i in range(0, (len(data)//8 - 2)))
  slot_offsets = [struct.unpack("<q", entry)[0] for entry in slot_entries]

  return (start_slot, record_start, slot_offsets)

def read_era_file(name):
  # Print contents of an era file, backwards
  with open(name, "rb") as f:

    # Seek to end of file to figure out the indices of the state and blocks
    f.seek(0, 2)

    groups = 0
    while True:
      if f.tell() < 8:
        break

      (start_slot, state_index_start, state_slot_offsets) = read_slot_index(f)

      print(
        "State slot:", start_slot,
        "state index start:", state_index_start,
        "offsets", state_slot_offsets)

      # The start of the state index record is the end of the block index record, if any
      f.seek(state_index_start)

      # This can underflow! Python should complain when seeking - ymmv
      prev_group = state_index_start + state_slot_offsets[0] - 8
      if start_slot > 0:
        (block_slot, block_index_start, block_slot_offsets) = read_slot_index(f)

        print(
          "Block start slot:", block_slot,
          "block index start:", block_index_start,
          "offsets", len(block_slot_offsets))

        if any((x for x in block_slot_offsets if x != 0)):
          # This can underflow! Python should complain when seeking - ymmv
          prev_group = block_index_start + [x for x in block_slot_offsets if x != 0][0] - 8

      print("Previous group starts at:", prev_group)
      # The beginning of the first block (or the state, if there are no blocks)
      # is the end of the previous group
      f.seek(prev_group) # Skip header

      groups += 1
    print("Groups in file:", groups)

def print_stats(name):
  with open(name, "rb") as f:
    sizes = {}
    entries = 0

    while True:
      (typ, data) = read_entry(f)

      if not typ:
        break
      entries += 1

      old = sizes.get(typ, (0, 0))
      sizes[typ] = (old[0] + len(data), old[1] + 1)

    print("Entries", entries)

    for k, v in dict(sorted(sizes.items())).items():
      print("type", k.hex(), "bytes", v[0], "count", v[1], "average", v[0] / v[1])

def print_help():
  print(sys.argv[0], "stats|era filename")
  exit(1)

if len(sys.argv) != 3:
  print_help()

if sys.argv[1] == "stats": print_stats(sys.argv[2])
elif sys.argv[1] == "era": read_era_file(sys.argv[2])
else: print_help()
