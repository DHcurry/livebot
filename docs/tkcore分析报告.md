## evidence_id

ev_e9cdc53f7a6cdcad378c09d39cde4b5791daa9ec26279db2e7efd212c001d33a

## subject.name

tkcore.exe

## subject.digest

| Key    | Value                                                            |
|--------|------------------------------------------------------------------|
| sha256 | 69dde4a69d33261efee74fa17def1b1ef14e008e2361f267326bf3f01c700b96 |

## subject.local_path

C:\Program Files\LuBot\core\tkcore.exe

## subject.format

pe

## subject.architecture

x86_64

## provider

| Key     | Value                               |
|---------|-------------------------------------|
| id      | rea-workflow                        |
| name    | REA composed investigation workflow |
| version | 1                                   |

## analysis_profile.provider

| Key     | Value                               |
|---------|-------------------------------------|
| id      | rea-workflow                        |
| name    | REA composed investigation workflow |
| version | 1                                   |

## analysis_profile.parameters.upstream_analysis_profile.provider

| Key     | Value  |
|---------|--------|
| id      | ghidra |
| name    | Ghidra |
| version | 12.1   |

## analysis_profile.parameters.upstream_analysis_profile.parameters.target_kind

executable

## analysis_profile.parameters.upstream_analysis_profile.parameters.target_format

pe

## analysis_profile.parameters.upstream_analysis_profile.parameters.executable_role

application

## analysis_profile.parameters.upstream_analysis_profile.parameters.managed

false

## analysis_profile.parameters.upstream_analysis_profile.parameters.native_aot_metadata

| Key                  | Value                       |
|----------------------|-----------------------------|
| contract_revision    | rtr-9.1-x64-pe-read-only-v5 |
| source_bytes         | 134217728                   |
| work_units           | 67108864                    |
| working_memory_bytes | 67108864                    |
| report_bytes         | 4194304                     |

## analysis_profile.parameters.upstream_analysis_profile.parameters.architecture

x86_64

## analysis_profile.parameters.upstream_analysis_profile.parameters.available_architectures

x86_64

## analysis_profile.parameters.upstream_analysis_profile.parameters.import_mode

ephemeral-source-immutable

## analysis_profile.parameters.upstream_analysis_profile.parameters.pdb_observations

program-info-v5

## analysis_profile.parameters.upstream_analysis_profile.parameters.annotation_policy

atomic-function-entry-metadata-v1

## analysis_profile.parameters.upstream_analysis_profile.parameters.load_image_observations

source-mappings-entry-context-v2

## analysis_profile.parameters.upstream_analysis_profile.parameters.function_body_evidence

complete-inclusive-ranges-v1

## analysis_profile.parameters.upstream_analysis_profile.parameters.function_references

complete-body-and-entry-reference-manager-v2

## analysis_profile.parameters.upstream_analysis_profile.parameters.call_relationship_coverage

function-body-call-coverage-v5

## analysis_profile.parameters.upstream_analysis_profile.parameters.function_dossier_coverage

observed-facets-and-call-relationships-v1

## analysis_profile.parameters.upstream_analysis_profile.parameters.string_inventory_evidence

defined-data-coverage-v1

## analysis_profile.parameters.upstream_analysis_profile.parameters.location_resolution

explicit-address-exact-entry-symbol-first-v3

## analysis_profile.parameters.upstream_analysis_profile.parameters.procedure_file_offset_resolution

address-first-unique-target-source-mapping-v2

## analysis_profile.parameters.upstream_analysis_profile.parameters.instruction_flow_evidence

decoded-return-pcode-v1

## analysis_profile.parameters.upstream_analysis_profile.parameters.instruction_references

exact-address-incoming-without-synthetic-entry-v2

## analysis_profile.parameters.upstream_analysis_profile.parameters.function_boundary_observations

ghidra-function-boundary-limitations-v4

## analysis_profile.parameters.upstream_analysis_profile.parameters.no_return_repair

disabled-windows-p0

## analysis_profile.parameters.upstream_analysis_profile.parameters.process_launch

official-headless-script-v1

## analysis_profile.parameters.upstream_analysis_profile.parameters.jump_table_evidence

typed-case-default-blocks-v1

## analysis_profile.parameters.upstream_analysis_profile.parameters.decompiler_jump_loads

true

## analysis_profile.parameters.upstream_analysis_profile.parameters.loader

auto-from-header

## analysis_profile.parameters.upstream_analysis_profile.parameters.language_id

auto-from-header

## analysis_profile.parameters.upstream_analysis_profile.parameters.compiler_spec_id

auto-default

## analysis_profile.parameters.upstream_analysis_profile.parameters.analyzer_preset

ghidra-default

## analysis_profile.parameters.upstream_analysis_profile.digest

c0486bbd8f927d2304b81335374257e7e4983c1bb423a8210d7bb888ad16da8a

## analysis_profile.parameters.source_limitations

provider-operation-caveats-v1

## analysis_profile.parameters.workflow_revision

4

## analysis_profile.digest

a34b147d3b0622d086da36d8bb0a09f4e0105d9163670d29c7ed97c0ab84870d

## predicate_type

rea.analysis

## operation

binary_overview

## parameters

| Key | Value |
|-----|-------|


## raw_result

null

## normalized_result.document

target-69dde4a69d33.exe

## normalized_result.image_base

0x140000000

## normalized_result.segments

| name    | start        | end          | length  | image_base  | address_space |
|---------|--------------|--------------|---------|-------------|---------------|
| Headers | 0x140000000  | 0x140000400  | 1024    | 0x140000000 | ram           |
| .text   | 0x140001000  | 0x1400dd800  | 903168  | 0x140000000 | ram           |
| .rdata  | 0x1400de000  | 0x140468e00  | 3714560 | 0x140000000 | ram           |
| .data   | 0x140469000  | 0x14046dfa8  | 20392   | 0x140000000 | ram           |
| .pdata  | 0x14046e000  | 0x140475800  | 30720   | 0x140000000 | ram           |
| .rsrc   | 0x140476000  | 0x140490e00  | 110080  | 0x140000000 | ram           |
| .reloc  | 0x140491000  | 0x140492a00  | 6656    | 0x140000000 | ram           |
| tdb     | 0xff00000000 | 0xff00001850 | 6224    | 0x140000000 | ram           |

## normalized_result.segment_count

8

## normalized_result.procedure_count

5153

## normalized_result.string_count

3266

## confidence

derived

## authority

shipped-artifact

## environment

null

## limitations

Derived by an REA composed workflow.,Ghidra (ghidra 12.1) read_binary_inventory_summary: Cancelling an active Ghidra request terminates its ephemeral database and discards session annotations. The selected target remains open; the next provider query imports the original artifact again.,Ghidra (ghidra 12.1) read_binary_inventory_summary: Counts use the complete defined-string inventory and the same local/external function inventory as list_strings and list_procedures. They do not establish discovery of undefined strings or unidentified functions.,Ghidra (ghidra 12.1) read_binary_inventory_summary: Default-space addresses use lowercase 0x-prefixed hexadecimal; other address spaces use <percent-encoded-space>:0x<hex>.,Ghidra (ghidra 12.1) read_binary_inventory_summary: Memory-block end addresses are exclusive; segment lengths use those observed address coordinates.,Ghidra (ghidra 12.1) read_binary_inventory_summary: Only Ghidra-defined string Data is observed; packed or undefined string bytes may be absent. Completeness applies to that inventory, and an empty search does not establish that text is absent from the artifact. If an address is known, use read_bytes and xrefs to inspect bytes and references.,Ghidra (ghidra 12.1) read_binary_inventory_summary: The Windows bridge uses authenticated IPv4 loopback because Node path-based IPC does not expose Java AF_UNIX sockets; the endpoint file contains no bearer token.,Ghidra (ghidra 12.1) read_binary_inventory_summary: The imported Program and temporary project are ephemeral and deleted on close. Annotation operations edit session database metadata; original executable bytes are never written.,Ghidra (ghidra 12.1) read_binary_inventory_summary: The session serves operations only after Ghidra reports default auto-analysis complete; incomplete analysis does not expose partial results.,Ghidra (ghidra 12.1) read_binary_inventory_summary: This session uses Ghidra 12.1. The bridge is verified against 12.1.4; other 12.1.x builds are accepted and the observed version is reported.,Ghidra (ghidra 12.1) read_binary_inventory_summary: Windows Ghidra P0 accepts native x86, x86-64, ARMNT (Thumb-2) and ARM64 PE applications and DLLs, and explicitly selected raw 6502 images; managed, hostile, sensitive, and mutable-path targets are unsupported.,Ghidra (ghidra 12.1) read_binary_inventory_summary: Windows sessions require the matching packaged Windows x64 native addon, local NTFS targets and runtimes, and Windows 10 or later. Native handles enforce path admission, private DACLs, and Job Object ownership automatically.

## relationship_coverage

null

## locations



## evidence_links

