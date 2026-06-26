<script lang="ts">
  import type { Verb, VerbAccess } from '$lib/generated/stores/schema.types';

  let { access, verb }: { access?: VerbAccess; verb: Verb } = $props();
</script>

{#if access}
  <div class="text-xs space-y-2">
    {#if verb === 'POST' || verb === 'PUT'}
      <div>
        <div class="text-[10px] font-bold uppercase tracking-widest text-blue-500 mb-1">in</div>
        {#if access.in == null}
          <em class="text-gray-400">all fields</em>
        {:else if access.in.length === 0}
          <em class="text-gray-400">none</em>
        {:else}
          <div class="flex flex-wrap gap-1 max-w-[200px]">
            {#each access.in as f}
              <span class="bg-blue-50 text-blue-700 border border-blue-200 px-1.5 py-0.5 rounded font-mono text-[10px]">{f}</span>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
    <div>
      <div class="text-[10px] font-bold uppercase tracking-widest text-emerald-500 mb-1">out</div>
      {#if access.out == null}
        <em class="text-gray-400">all fields</em>
      {:else if access.out.length === 0}
        <em class="text-gray-400">none</em>
      {:else}
        <div class="flex flex-wrap gap-1 max-w-[200px]">
          {#each access.out as f}
            <span class="bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.5 rounded font-mono text-[10px]">{f}</span>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}
