@twocol{
@ {
What is the definition of @math{\Z[i]}?
}

@ {
@math|{ \Z[i] := \{ a+bi \mid a,b \in \Z \} }|.
}
}

@twocol{
@ {
In terms of rings, what is a unit?
}

@ {
We call an element a unit if it has a multiplicative inverse in the ring.

For example, in the ring @math{R}, we call @math{y \in R} a unit if there exists some @math{x \in R} st. @math{xy = 1}.
}
}

@twocol{
@ {
Let @math|{ (a+bi), (c+di) \in \Z[i] }|. Explain why @math{(a+bi)(c+di) = 1} @math{\implies} @math{(a-bi)(c-di) = 1}

@italic{Hint:} expand.
}

@ {
@italic{Proof:}

@math|{
\begin{aligned}
(a+bi)(c+di) &= (ac - bd) + (ad + bc)i \quad ^{\text{(*)}} \\
(a-bi)(c-di) &= (ac - bd) + (- ad - bc)i
\end{aligned}
}|
}
}

@twocol{
@ {
Suppose @math|{ \text{(*)} = 1 }|. What can we say about this?
}

@ {
Suppose @math|{ \text{(*)} = 1 }|. Then we have a system of equations
@Math|{
\begin{cases}
ad + bc = 0 \\
ac - bd = 1
\end{cases}
}|
Given this system, we can also say @Math|{
\begin{cases}
-ad - bc = 0 \\
ac - bd = 1
\end{cases}
}|
Thus, by regrouping, @math{(a-bi)(c-di) = 1}. @math{\square}
}
}

@twocol{
@ {
Use this important lemma to prove the units in @math|{ \Z[i] }| are @math|{ \{ \pm 1, \pm i \} }|.
}

@ {
Suppose @math|{ (a+bi)(c+di) = 1 \,^{(1)} }|, then @math|{ (a-bi)(c-di) = 1 \,^{(2)} }|.

@math{(a+bi)(a-bi) = a^2 + b^2 \geq 0}, @math{(c+di)(c-di) = c^2 + d^2 \geq 0}.

@math{(1) \cdot (2)} gives us
@math{a^2 + b^2 + c^2 + d^2 = 1}
}
}

@twocol{
@ {
Suppose @math{a = 1}, and the other variables being @math{0}.
}

@ {
}
}

@twocol{
@ {
Prove that in a field @math{F}, there is no zero divisors.

I'll set up the proof:

For contradiction, suppose there exists @math{a \in F \, (a \neq 0)} st.
@math{ab = 0} for some non-zero @math{b \in F}.
}

@ {
Then @math|{\exists a^{-1} \in F}| st. @math|{a^{-1}a = 1}|.

Thus @math|{a^{-1}ab = 0}|, and this shows
@math{b = 0}.

Contradiction.
}
}

@twocol{
@ {
Keep this lemma in mind. Next time, we will use it to prove the big theorem of @math{F[x]/p(x)}.
}

@ {}
}
