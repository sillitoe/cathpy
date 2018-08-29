import logging
import os
import re
import tempfile
import unittest

from cathpy import seqio

from . import testutils

logger = logging.getLogger(__name__)

class TestSequence(testutils.TestBase):

    def setUp(self):
        self.stockholm_file = os.path.join(os.path.dirname(__file__), 'data', 'test.sto')

        self.fasta_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)

        # removing gaps from alignments
        self.fasta_contents = '''
>id1
----AKGHP---GPKAPGPAK---
>id2
-AGPAK-HP--PGPKAPPPAK-G-
'''[1:]
        self.fasta_contents_without_gaps = '''
>id1
---AKGHP-GPKAPGPAK-
>id2
AGPAK-HPPGPKAPPPAKG
'''[1:]

        # merging funfam alignments into structural alignments
        self.fasta_aln_ref = '''
>ref1
---AKGHP--GPKAPGPAK--
>ref2
CGCAKGH-PKA--APGP--GT
'''[1:]

        self.fasta_aln_merge1 = '''
>ref1
-AK-GHPGP--KAPG--PAK
>src1.1
GAGGG-PGPGKKAPGG--AK
>src1.2
PAGGCCPGP--KAPGGSAA-
'''[1:]

        self.fasta_aln_merge2 = '''
>ref2
--CGC--AKGHPK-AAPGPGT-
>src2.1
--CGC-PAKHPPKGAA-GPGPA
>src2.2
GHCHCFSAKHPPK-AAHGPGPA
'''[1:]

        self.fasta_aln_after_merge1 = '''
>ref1
---.AK.GHP--GP..KAPG..PAK--
>ref2
AKG.AK.GH-PKA-..-APG..P--GP
>src1.1
---gAGgG.P--GPgkKAPGg..AK--
>src1.2
---pAGgCcP--GP..KAPGGsAA.--
'''[1:]

        self.fasta_aln_after_merge2 = '''
>ref1  
..---...AK.GHP--.GP..KAPG..PAK--.
>ref2  
..CGC...AK.GH-PK.A-..-APG..P--GT.
>src1.1
..---g..AGgG-P--.GPgkKAPGg--AK--.
>src1.2
..---p..AGgCCP--.GP--KAPGgsAA---.
>src2.1
--CGC--pAK-HP-PKgA----A-G--P--GPa
>src2.2
ghCHC-fsAK-HP-PK-A----AHG--P--GPa
'''[1:]

        self.fasta_file.write(self.fasta_contents)
        self.fasta_file.seek(0)
    
    def tearDown(self):
        pass
        #os.remove(self.fasta_file.name)

    def test_aa(self):
        ala = seqio.AminoAcids.get_by_id('A')
        self.assertEqual(ala.one, 'A')
        self.assertEqual(ala.three, 'ala')
        self.assertEqual(ala.word, 'alanine')

    def test_create_sequence(self):
        seq = seqio.Sequence('id1/23-123', '---AKGHP--GPKAPGPAK--')
        self.assertEqual(seq.id, 'id1')
        self.assertEqual(len(seq.segs), 1)
        self.assertEqual(seq.segs[0].start, 23)
        self.assertEqual(seq.segs[0].stop, 123)
        self.assertEqual(seq.seq, '---AKGHP--GPKAPGPAK--')
        self.assertEqual(seq.get_res_at_offset(0), '-')
        self.assertEqual(seq.get_res_at_offset(3), 'A')
        seq.insert_gap_at_offset(5)
        self.assertEqual(seq.seq, '---AK-GHP--GPKAPGPAK--')
        seq.insert_gap_at_offset(-3, gap_char='.')
        self.assertEqual(seq.seq, '---AK-GHP--GPKAPGPA.K--')

    def test_sequence_methods(self):
        seq = seqio.Sequence('id1/23-123', '---AKGHP--GPKAPGPAK--')
        self.assertEqual(seq.get_offset_at_seq_position(1), 3) # seq pos '1' 'A' -> offset '3' 
        self.assertEqual(seq.get_res_at_seq_position(2), 'K')
        self.assertEqual(seq.get_seq_position_at_offset(5), 3)  # offset 5 'G' -> seq pos 3 'AKG'
        self.assertEqual(seq.get_res_at_offset(5), 'G')

    def test_sequence_lower_case(self):
        seq = seqio.Sequence('id1/23-123', '---AKGHP--GPKAPGPAK--')
        seq.lower_case_at_offset(6)
        self.assertEqual(seq.seq, '---AKGhP--GPKAPGPAK--') 

    def test_create_segment(self):
        seg = seqio.Segment(1, 10)
        self.assertEqual(seg.start, 1)
        self.assertEqual(seg.stop, 10)
        self.assertEqual(str(seg), '1-10')

    def test_split_hdr(self):
        hdr = seqio.Sequence.split_hdr('domain|1cukA01/12-134_178-234')
        self.assertEqual(hdr['id'], '1cukA01')
        self.assertEqual(hdr['id_type'], 'domain')
        self.assertIsInstance(hdr['segs'][0], seqio.Segment)
        self.assertEqual(hdr['segs'][0].start, 12)
        self.assertEqual(hdr['segs'][0].stop, 134)
        self.assertIsInstance(hdr['segs'][1], seqio.Segment)
        self.assertEqual(str(hdr['segs'][1]), '178-234')
        self.assertEqual(hdr['id_ver'], None)

    def test_read_fasta_filename(self):
        aln = seqio.Alignment.new_from_fasta(self.fasta_file.name)
        self.assertEqual(aln.count_sequences, 2)
        seqs = aln.seqs
        self.assertEqual(seqs[0].id, 'id1')
        self.assertEqual(seqs[1].id, 'id2')

    def test_read_fasta_fileio(self):
        self.fasta_file.seek(0)
        aln = seqio.Alignment.new_from_fasta(self.fasta_file)
        self.assertEqual(aln.count_sequences, 2)

    def test_read_stockholm_file(self):
        aln = seqio.Alignment.new_from_stockholm(self.stockholm_file)
        self.assertEqual(aln.count_sequences, 51)

    def test_read_fasta_str(self):
        aln = seqio.Alignment.new_from_fasta(self.fasta_contents)
        self.assertEqual(aln.count_sequences, 2)

    def test_remove_gaps(self):
        self.log_title('remove_gaps')
        self.fasta_file.seek(0)
        aln = seqio.Alignment.new_from_fasta(self.fasta_contents)
        self.assertEqual(aln.count_sequences, 2)
        new_aln = aln.remove_alignment_gaps()
        new_seqs = new_aln.seqs
        seqs_no_gap = "".join([s.to_fasta() for s in new_seqs])
        self.assertEqual(seqs_no_gap, self.fasta_contents_without_gaps)

    def test_copy_aln(self):
        self.log_title('copy_aln')
        aln_ref = seqio.Alignment.new_from_fasta(self.fasta_aln_ref)
        aln_copy = aln_ref.copy()
        self.assertNotEqual(aln_copy, aln_ref)
        self.assertEqual(str(aln_copy), str(aln_ref))

    def test_aln_add_gap(self):
        self.log_title('aln_add_gap')        
        aln = seqio.Alignment.new_from_fasta(self.fasta_aln_ref)
        self.assertEqual(aln.seqs[0].seq, '---AKGHP--GPKAPGPAK--')
        self.assertEqual(aln.seqs[1].seq, 'CGCAKGH-PKA--APGP--GT')
        aln.insert_gap_at_offset(4)
        self.assertEqual(aln.seqs[0].seq, '---A-KGHP--GPKAPGPAK--')
        self.assertEqual(aln.seqs[1].seq, 'CGCA-KGH-PKA--APGP--GT')
        aln.insert_gap_at_offset(-3, gap_char='.')
        self.assertEqual(aln.seqs[0].seq, '---A-KGHP--GPKAPGPA.K--')
        self.assertEqual(aln.seqs[1].seq, 'CGCA-KGH-PKA--APGP-.-GT')

    def test_merge_aln(self):
        aln_ref = seqio.Alignment.new_from_fasta(self.fasta_aln_ref)
        self.assertEqual(aln_ref.count_sequences, 2)
        aln_merge1 = seqio.Alignment.new_from_fasta(self.fasta_aln_merge1)
        self.assertEqual(aln_merge1.count_sequences, 3)
        aln_merge2 = seqio.Alignment.new_from_fasta(self.fasta_aln_merge2)
        self.assertEqual(aln_merge2.count_sequences, 3)

        aln_ref.merge_alignment(aln_merge1, 'ref1')
        aln_after_merge1 = seqio.Alignment.new_from_fasta(self.fasta_aln_after_merge1)
        self.assertEqual(aln_after_merge1.count_sequences, 4)
        self.assertEqual(aln_ref.count_sequences, 4)

        aln_ref.merge_alignment(aln_merge2, 'ref2')
        aln_after_merge2 = seqio.Alignment.new_from_fasta(self.fasta_aln_after_merge2)
        self.assertEqual(aln_after_merge2.count_sequences, 6)
        self.assertEqual(aln_ref.count_sequences, 6)        

if __name__ == '__main__':
    unittest.main()