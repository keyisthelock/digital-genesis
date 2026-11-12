"""Generated, data-only curriculum tasks and independent scoring."""
from dataclasses import dataclass
from fractions import Fraction
import random
import re


@dataclass(frozen=True)
class Task:
    key: str
    chapter: str
    domain: str
    skill: str
    level: int
    question: str
    data: dict
    expected: object
    source: str
    cost: int = 1
    risk: float = 0.

    def packet(self):
        return dict(skill=self.skill, question=self.question, data=self.data)


CHAPTERS = ("The Archive","The Academy","The Forge","The Citadel","The Open Horizon")
NOTES = {
    "slope": ("The Academy", "Slope measures change in vertical coordinate per change in horizontal coordinate."),
    "probability": ("The Academy", "An event probability is its favorable equally likely outcomes divided by all equally likely outcomes."),
    "gravity": ("The Forge", "In an ideal constant-acceleration drop from rest, displacement grows quadratically with time. Ignore drag in this virtual model."),
    "stoichiometry": ("The Forge", "In a balanced reaction, coefficients give relative amounts. The reactant with the lowest number of available reaction units limits production."),
    "circuit": ("The Forge", "For resistors in series, sum resistance. With an ideal fixed source, current is voltage divided by the total resistance."),
    "dedup": ("The Citadel", "Stable deduplication keeps the first occurrence of each value. Sorting would change encounter order."),
    "access": ("The Citadel", "In a synthetic access review, grant only the actions explicitly needed by the role. Unneeded grants should be removed."),
    "history": ("The Archive", "The archived 1.7.1 report records 11 successes in 20 native survival-and-eat trials, 1 in 20 random and 5 in 20 fixed-reactive. The experiment was a short project benchmark."),
    "poetry": ("The Archive", "An image uses concrete sensory detail. A line constraint can be verified mechanically; aesthetic quality needs human judgment."),
    "design": ("The Open Horizon", "A controlled experiment changes one factor while holding other conditions steady; use independent repetitions.")
}
NOTES.update({
    "algebra": ("The Academy", "Subtract the constant term before dividing by the nonzero coefficient."),
    "geometry": ("The Academy", "For an axis-aligned rectangle, multiply side lengths for area."),
    "trig": ("The Academy", "The sine of an acute angle is opposite-leg length divided by hypotenuse length."),
    "calculus": ("The Academy", "Use the power rule to differentiate a quadratic. A constant term has zero derivative."),
    "matrix": ("The Academy", "A square two-by-two determinant is the main-diagonal product minus the other diagonal product."),
    "logic": ("The Academy", "If P implies Q and P holds, Q follows by modus ponens. Affirming Q alone cannot establish P."),
    "thermal": ("The Forge", "For an ideal sample with constant heat capacity, energy equals mass times specific heat capacity times temperature increase."),
    "ecology": ("The Forge", "Isolate a light treatment by matching water, plant variety, and sampling time; repeat with separate plants."),
    "queue": ("The Citadel", "A FIFO queue removes the oldest element first. This exercise uses data-only operations."),
    "authentication": ("The Citadel", "Authentication verifies identity. Authorization checks which actions an identified actor is permitted to perform."),
    "ethics": ("The Archive", "A documented trial result is evidence. A judgment about acceptable trade-offs is a value position."),
    "integrated": ("The Open Horizon", "A sound virtual project defines a measurable result, holds irrelevant conditions fixed and compares against a baseline."),
    "dedup_program": ("The Citadel", "To remove duplicate values while preserving order, record seen values and emit the first occurrence only."),
    "secure_review": ("The Citadel", "Keep user-supplied data separate from a database command by binding query parameters.")
})
REGISTRY = {
    "slope": ("math",1), "probability": ("math",2), "gravity": ("science",1),
    "stoichiometry": ("science",2), "circuit": ("engineering",2), "dedup": ("engineering",1),
    "access": ("cyber_defense",1), "history": ("history_philosophy",1),
    "poetry": ("creative",1), "design": ("science",2)
}
INTRO_SKILLS=tuple(REGISTRY)
REGISTRY.update({
    **{k:("math",2) for k in ("algebra","geometry","trig","calculus","matrix","logic")},
    "thermal":("science",2),"ecology":("science",2),"queue":("engineering",2),
    "authentication":("cyber_defense",2),"ethics":("history_philosophy",2),
    "integrated":("engineering",3),"dedup_program":("engineering",3),"secure_review":("cyber_defense",2)
})


def generate(skill, seed, index=0):
    rng = random.Random(seed*1009+index*59)
    a,b,c = rng.sample(range(2,13),3)
    chapter,_ = NOTES[skill]
    domain,level = REGISTRY[skill]
    if skill=="slope":
        data = dict(points=[[a,b],[a+c,b+a]])
        question,expected = "Find the slope between the two points. Return a number or exact fraction as text.",Fraction(a,c)
    elif skill=="probability":
        data = dict(red=a,blue=b)
        question,expected = "One ball is drawn uniformly. What is the probability of red? Return an exact fraction.",Fraction(a,a+b)
    elif skill=="gravity":
        data = dict(acceleration=2*a,seconds=b)
        question,expected = "In this virtual drop from rest under constant acceleration, calculate displacement. Return a number.",a*b*b
    elif skill=="stoichiometry":
        data = dict(reaction="2 A + B -> 3 C",A=a,B=b)
        question,expected = "Using complete whole reaction units, how many units of C can form? Return an integer.",3*min(a//2,b)
    elif skill=="circuit":
        data = dict(volts=a,resistors=[b,c])
        question,expected = "Find current in the ideal series circuit. Return an exact fraction.",Fraction(a,b+c)
    elif skill=="dedup":
        items = [b,a,b,c,a]
        data = dict(values=items)
        question,expected = "Return a JSON array retaining the first occurrence of each value, in order.",list(dict.fromkeys(items))
    elif skill=="access":
        items = ["view_manual","edit_roster","approve_budget","export_contacts"]
        rng.shuffle(items)
        data = dict(required=["view_manual"],assigned=items[:])
        question,expected = "In this fictional role audit, return the excess grants as a JSON array. Order does not matter.",sorted(set(items)-{"view_manual"})
    elif skill=="history":
        data = dict(claim="Omega collected food in every 1.7.1 held-out survival trial.",
                    labels=["supported","contradicted","unknown"])
        question,expected = "Classify this claim about the project archive. Use unknown if you lack the source.", "contradicted"
    elif skill=="poetry":
        data = dict(motif=rng.choice(("rain","stone","wind","river")),lines=2)
        question,expected = "Write two original poetic lines. Include the motif at least once. Return a string with a line break.",None
    elif skill=="design":
        data = dict(options={"A":"Change food and light together","B":"Change only food; repeat both conditions",
                             "C":"Use one observation without a comparison"})
        question,expected = "Which comparison isolates the effect of food? Return the option letter.", "B"
    elif skill=="algebra":
        data=dict(coefficient=a,constant=b,total=a*c+b)
        question,expected="Solve coefficient*x + constant = total for x.",c
    elif skill=="geometry":
        data=dict(width=a,height=b)
        question,expected="Find the area of the rectangle.",a*b
    elif skill=="trig":
        data=dict(opposite=3*a,adjacent=4*a,hypotenuse=5*a)
        question,expected="Find the exact sine of the angle with the given opposite side.",Fraction(3,5)
    elif skill=="calculus":
        data=dict(quadratic_coefficient=a,linear_coefficient=b,x=c)
        question,expected="Find the derivative of the quadratic a*x^2 + b*x at the given x.",2*a*c+b
    elif skill=="matrix":
        data=dict(matrix=[[a,b],[c,a]])
        question,expected="Calculate this two-by-two determinant.",a*a-b*c
    elif skill=="logic":
        data=dict(premises=["If the sample boils, a sensor triggers.","The sample boils."],
                  options={"A":"The sensor triggers","B":"The sensor never triggers","C":"The conclusion is unrelated"})
        question,expected="Which conclusion follows from both premises? Return its letter.","A"
    elif skill=="thermal":
        data=dict(mass=a,specific_heat=b,temperature_rise=c)
        question,expected="Find energy added to this ideal virtual sample in consistent units.",a*b*c
    elif skill=="ecology":
        data=dict(options={"A":"Change light and water together","B":"Change only light, repeat with matched plants",
                           "C":"Compare unrelated species at different times"})
        question,expected="Select the design that isolates the effect of light on seedlings.","B"
    elif skill=="queue":
        data=dict(initial=[a,b],append=c)
        question,expected="Remove one item from the FIFO queue, then append the given item. Return the remaining queue.",[b,c]
    elif skill=="authentication":
        data=dict(options={"A":"Authentication","B":"Authorization","C":"Compression"})
        question,expected="Which term describes checking whether a signed-in librarian may edit a record?","B"
    elif skill=="ethics":
        data=dict(statement="We should prioritize transparency even if the report takes longer.",
                  options={"A":"A measured outcome","B":"A value judgment","C":"A timestamp"})
        question,expected="Classify the quoted statement. Return its option letter.","B"
    elif skill=="integrated":
        data=dict(options={"A":"Measure energy and food against a paired control with identical starting stocks",
                           "B":"Choose the most persuasive narrative","C":"Report only the best seed"})
        question,expected="Choose a fair evaluation for a simulated foraging policy.","A"
    elif skill=="dedup_program":
        data=dict(ops=["keep_first","reverse","sort"],max_ops=2,example_input=[b,a,b,c])
        question=("Write a bounded JSON array of operation names to keep first occurrences in input order. "
                  "Your program will be tested on unseen arrays.")
        expected=[[b,a,b,c],[],[c,c,c],[a,c,b,a],[b,c,a,c,b]]
    elif skill=="secure_review":
        data=dict(options={"A":"Join form text directly into the database command",
                           "B":"Bind form text as a parameter","C":"Change the form label"})
        question,expected="Which change keeps input data separate from database commands?","B"
    else:
        raise ValueError("Unknown skill")
    return Task(f"{skill}-{seed}-{index}",chapter,domain,skill,level,question,data,expected,skill)


def score(task, answer):
    if task.skill=="dedup_program":
        ops={"keep_first":lambda seq:list(dict.fromkeys(seq)), "reverse":lambda seq:list(reversed(seq)),
             "sort":sorted}
        if type(answer) is not list or not 1<=len(answer)<=2 or any(type(x) is not str or x not in ops for x in answer):
            return False,"program_rejected"
        for case in task.expected:
            actual=case[:]
            for op in answer:
                actual=ops[op](actual)
            if actual!=list(dict.fromkeys(case)):
                return False,"hidden_case_failure"
        return True,"program_tests_passed"
    if task.skill=="poetry":
        if not isinstance(answer,str):
            return False,"creative_constraint"
        lines = [s.strip() for s in answer.splitlines() if s.strip()]
        ok = len(lines)==task.data["lines"] and bool(re.search(r"\b"+task.data["motif"]+r"\b",answer,re.I))
        return ok,"creative_constraints_only"
    if isinstance(task.expected,(Fraction,int)):
        if type(answer) not in (int,float,str) or len(str(answer))>40:
            return False,"answer_format"
        if not re.fullmatch(r"[+-]?\d+(?:\.\d+|/\d+)?",str(answer).strip()):
            return False,"answer_format"
        try:
            value = Fraction(str(answer).strip())
            ok = value==task.expected
        except (ValueError,ZeroDivisionError):
            return False,"answer_format"
    elif isinstance(task.expected,list):
        if type(answer) is not list or len(answer)>20 or any(type(v) not in (str,int) for v in answer):
            return False,"answer_format"
        ok = sorted(answer)==task.expected if task.skill=="access" and all(isinstance(x,str) for x in answer) else answer==task.expected
    else:
        ok = type(answer) is str and answer.strip().lower()==task.expected.lower()
    return ok,"verified" if ok else "incorrect"


def solve_method(task, method):
    """A transparent limited reference policy and explicit deterministic tools."""
    d = task.data
    if task.skill=="slope":
        (x,y),(u,v)=d["points"]
        return str(Fraction(v-y,u-x) if method=="worked" else Fraction(u-x,v-y))
    if task.skill=="probability":
        return str(Fraction(d["red"],d["red"]+d["blue"] if method=="worked" else d["blue"]))
    if task.skill=="gravity":
        return d["acceleration"]*d["seconds"]**2//(2 if method=="worked" else 1)
    if task.skill=="stoichiometry":
        return 3*min(d["A"]//2,d["B"]) if method=="worked" else 3*min(d["A"],d["B"])
    if task.skill=="circuit":
        r=d["resistors"]
        return str(Fraction(d["volts"],sum(r) if method=="worked" else r[0]))
    if task.skill=="dedup":
        return list(dict.fromkeys(d["values"])) if method=="worked" else sorted(set(d["values"]))
    if task.skill=="access":
        return [grant for grant in d["assigned"] if grant not in d["required"]] if method=="worked" else d["assigned"]
    if task.skill=="design":
        return "B" if method=="worked" else "A"
    if method!="worked":
        return "unknown"
    if task.skill=="algebra":
        return (d["total"]-d["constant"])//d["coefficient"]
    if task.skill=="geometry":
        return d["width"]*d["height"]
    if task.skill=="trig":
        return str(Fraction(d["opposite"],d["hypotenuse"]))
    if task.skill=="calculus":
        return 2*d["quadratic_coefficient"]*d["x"]+d["linear_coefficient"]
    if task.skill=="matrix":
        (a,b),(c,e)=d["matrix"]
        return a*e-b*c
    if task.skill=="thermal":
        return d["mass"]*d["specific_heat"]*d["temperature_rise"]
    if task.skill=="queue":
        return d["initial"][1:]+[d["append"]]
    if task.skill=="dedup_program":
        return ["keep_first"]
    if task.skill in ("logic","ecology","authentication","ethics","integrated","secure_review"):
        return "unknown"  # Preserve these reasoning exercises for agent answers.
    return "unknown"
