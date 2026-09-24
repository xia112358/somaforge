"""Persistent independent endpoint rollouts; one batched action per update."""
import torch

from .full1000_training_variants import recovery_transition


class ParallelRolloutPool:
    def __init__(self, reference, training_indices, successor, size, *,
                 recover_failed_states=False, max_episode_steps=64, max_retries=8):
        if recover_failed_states:
            raise ValueError('Failed next-contact predictions terminate; retries are disabled')
        if size < 1 or max_episode_steps < 1 or max_retries < 1:
            raise ValueError('Pool size and episode limits must be positive')
        if not len(training_indices): raise ValueError('Empty training pool')
        self.reference=reference
        self.training_indices=training_indices
        self.size=size
        self.recover_failed_states=recover_failed_states
        self.max_episode_steps=max_episode_steps
        self.max_retries=max_retries
        allowed=torch.zeros(len(successor),dtype=torch.bool,device=successor.device)
        allowed[training_indices]=True
        valid=(successor >= 0) & allowed[successor.clamp_min(0)]
        self.successor=torch.where(valid,successor,-1)
        self.indices=self.draw_references(size)
        self.observation={k:v[self.indices].detach().clone() for k,v in reference.items()}
        self.age=torch.zeros_like(self.indices)
        self.retries=torch.zeros_like(self.indices)
        self.cursor=0

    def draw_references(self, count):
        return self.training_indices[torch.randint(len(self.training_indices),(count,),device=self.training_indices.device)]

    def batch(self, count):
        if not 1 <= count <= self.size: raise ValueError('Invalid parallel batch size')
        slots=(torch.arange(count,device=self.indices.device)+self.cursor)%self.size
        self.cursor=(self.cursor+count)%self.size
        return slots,self.indices[slots],{k:v[slots] for k,v in self.observation.items()}

    @torch.no_grad()
    def update(self, slots, q, observed, completed, recoverable, make_observation):
        indices=self.indices[slots]
        next_indices,keep,advance,retry=recovery_transition(indices,self.successor,completed,
            recoverable if self.recover_failed_states else torch.zeros_like(recoverable))
        age=self.age[slots]+1
        retries=torch.where(retry,self.retries[slots]+1,0)
        terminal=completed & (self.successor[indices] < 0)
        invalid=~completed
        timeout=keep & ((age >= self.max_episode_steps) | (retries >= self.max_retries))
        reset=~keep | timeout
        references=self.draw_references(len(slots))
        # q is the actual raw prediction, without correction or future q.
        # Fresh observations come from its already executed Newton query.
        chosen=(~reset).nonzero().flatten()
        # Never construct a successor observation from a failed output.
        fresh=(make_observation(q[chosen].detach(),next_indices[chosen],observed,chosen)
               if len(chosen) else None)
        for key,storage in self.observation.items():
            storage[slots]=self.reference[key][references]
            if len(chosen): storage[slots[chosen]]=fresh[key].detach()
        self.indices[slots]=torch.where(reset,references,next_indices)
        self.age[slots]=torch.where(reset,0,age)
        self.retries[slots]=torch.where(reset,0,retries)
        return dict(advances=(advance & ~reset).sum(),retries=(retry & ~reset).sum(),
            resets=reset.sum(),terminal_resets=terminal.sum(),invalid_resets=invalid.sum(),
            timeout_resets=timeout.sum(),generated_inputs=(self.age[slots] > 0).sum())

    def state_dict(self):
        return {'indices':self.indices.detach().cpu(),'age':self.age.detach().cpu(),
            'retries':self.retries.detach().cpu(),'cursor':self.cursor,
            'observation':{k:v.detach().cpu() for k,v in self.observation.items()}}
