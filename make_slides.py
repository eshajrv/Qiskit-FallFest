from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

W, H = landscape(letter)
doc = SimpleDocTemplate("Noise_Busters_Presentation.pdf", pagesize=landscape(letter),
                        leftMargin=0.7*inch, rightMargin=0.7*inch, topMargin=0.6*inch, bottomMargin=0.5*inch,
                        title="Noise Busters: shot-budget-aware SLC on ibm_kingston", author="Amirshayan")
NAVY = colors.HexColor("#1b2a49"); GREY = colors.HexColor("#555555")
h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=26, textColor=NAVY, leading=32, spaceAfter=14)
h0 = ParagraphStyle("h0", parent=h1, fontSize=34, leading=40, spaceAfter=20)
body = ParagraphStyle("b", fontName="Helvetica", fontSize=15, leading=21, spaceAfter=6)
bul = ParagraphStyle("bul", parent=body, leftIndent=18, bulletIndent=4)
small = ParagraphStyle("s", parent=body, fontSize=11, leading=14, textColor=GREY)
mono = ParagraphStyle("m", parent=body, fontName="Courier", fontSize=12, leading=16)
tstyle = TableStyle([("FONT", (0,0), (-1,0), "Helvetica-Bold", 12), ("FONT", (0,1), (-1,-1), "Helvetica", 12),
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e8eef5")), ("LINEBELOW", (0,0), (-1,0), 1, NAVY),
    ("LINEBELOW", (0,-1), (-1,-1), 0.5, GREY), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5)])


def slide(title, *items):
    out = [Paragraph(title, h1)]
    for it in items:
        out.append(Paragraph(it, bul, bulletText="•") if isinstance(it, str) else it)
    out.append(PageBreak())
    return out


def footer(c, d):
    c.saveState(); c.setFont("Helvetica", 9); c.setFillColor(GREY)
    c.drawString(0.7*inch, 0.3*inch, "Noise Busters, IBM Qiskit Fall Fest 2026, Berkeley. All jobs on ibm_kingston (Heron), instance student-67.")
    c.drawRightString(W-0.7*inch, 0.3*inch, str(d.page)); c.restoreState()


ZZ = "&lt;Z6 Z7&gt;"
S = [Paragraph("Noise Busters", h0),
     Paragraph("Shot-budget-aware shaded lightcones (SLC) on ibm_kingston", h1),
     Spacer(1, 10),
     Paragraph("Amirshayan, SFSU. IBM Qiskit Fall Fest 2026, Berkeley, 10 October 2026.", body),
     Paragraph(f"Final answer: {ZZ} = 0.6788 ± 0.0046, grader score 51.8", body),
     Paragraph("Every number reproduces from the job IDs on the last slide.", small),
     PageBreak()]

S += slide("1. Method: PEC with shaded lightcones, tuned to the shot budget",
    "Learn a Pauli-Lindblad noise model for the 3 unique layers (NoiseLearnerV3, about 88 s of QPU).",
    "Shaded lightcones cancel only the noise terms that reach Z6 Z7. Overhead gamma² drops from 7.9x (full PEC) to 3.1x.",
    "Shot-budget rule: pick the bias tolerance that minimizes sqrt(b² + gamma²/N) instead of cancelling everything and drowning in shot noise.",
    "Readout: TREX rescaling plus edge post-selection on spectator qubits.")

S += slide("2. Results",
    Table([["Method", "Mirror (ideal 1.0)", "Run 1 (256 x 128)", "Run 2 (512 x 256)"],
           ["Raw", "0.586 ± 0.005", "0.5450 ± 0.0046", "0.5710 ± 0.0023"],
           ["TREX + post-selection", "0.648 ± 0.005", "0.5947 ± 0.0052", "0.6199 ± 0.0025"],
           ["SLC + TREX + post-selection", "1.019 ± 0.043", "0.6938 ± 0.0102", "0.6749 ± 0.0052"]],
          colWidths=[3.4*inch, 2.1*inch, 2.1*inch, 2.1*inch], style=tstyle),
    Spacer(1, 10),
    "Mirror check passes: the pipeline is wired correctly.",
    "Final answer = inverse-variance mean of the two SLC edge values: 0.6788 ± 0.0046, score 51.8.",
    "Submissions 0 to 48.1 to 51.8, each chosen by a rule written before seeing the data. Never compared with the exact value.")

S += slide("3. Honest finding: the limit is bias from a stale noise model, and the queue makes it worse",
    "Error 0.0165 is 3.5x the statistical error. 4x more shots did not help.",
    "Raw value drifted 5 sigma in 12 minutes while run 2 reused the 14:12 model. Noise models go stale in about 15 minutes.",
    "Fix attempted: fresh model plus executor back to back. The job sat in a queue that grew from 8 to 92 jobs and never ran; cancelled at the 4:40 cutoff, nothing new submitted.",
    "Lesson: queue delay is itself a mitigation bias. Learning and execution must run in one session.")

S += slide("4. Reproduction: job IDs (ibm_kingston, seed_transpiler=1234)",
    Paragraph("Chain: [30, 29, 38, 49, 48, 47, 46, 45, 44, 43, 42, 41, 36, 21, 20]", mono),
    Table([["Job ID", "What", "Time PT"],
           ["db5ajpcvf2bc73cvks4g", "Baseline Estimator, 10k shots (score 0)", "14:11"],
           ["db5ak64vf2bc73cvkshg", "Noise learning, scored circuit", "14:12"],
           ["db5al9qmb58s738a7sa0", "Run 1 executor, 256 x 128, tol 1e-3", "14:18"],
           ["db5armklf4us73c3pn20", "Run 2 executor, 512 x 256, tol 1e-6", "14:30"],
           ["db5as9clf4us73c3pof0", "Mirror noise learning", "14:33"],
           ["db5av2amb58s738a8f70", "Mirror executor, 256 x 128", "14:39"],
           ["db5bq4svf2bc73cvmidg", "Fresh noise learning, queued, cancelled at cutoff", "15:32"]],
          colWidths=[2.6*inch, 5.0*inch, 1.2*inch], style=tstyle),
    Spacer(1, 8),
    Paragraph("Reattach with service.job(id), then select_errors and postprocess from nb_pipeline.py.", small))

doc.build(S, onFirstPage=footer, onLaterPages=footer)
print("wrote Noise_Busters_Presentation.pdf")
