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
