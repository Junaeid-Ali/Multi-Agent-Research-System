from agents import build_search_agent, build_reader_agent, critic_chain,writer_chain

def run_research_pipeline(topic:str)-> dict:
    state={}

    #search agent working

    search_agent=build_search_agent()
    search_result=search_agent.invoke({
        "messages":[("user", f"Find recent, reliable and detailed information about: {topic}")]
    })

    state["search_result"]=search_result["messages"][-1].content

    #reader agent

    reader_agent=build_reader_agent()
    reader_result=reader_agent.invoke({
        "messages": [("user",
            f"Based on the following search results about '{topic}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Search Results:\n{state['search_result'][:800]}"
        )]
    })

    state['scraped_result']=reader_result["messages"][-1].content

    print("\n Scraped Content",state["scraped_result"])

    research_combined=(
        f"Search Result: {state['search_result']}\n\n"
        f"Detailed Explained Content: {state['scraped_result']}"
    )


    state['report']=writer_chain.invoke({
        "topic":topic,
        "research":research_combined
    })


    print("\n Final Report \n",state['report'])

    #critic Report 
    state['feedback']=critic_chain.invoke({
        "report":state["report"]
    })

    print("\n Critic Report \n",state["feedback"])

    return state

if __name__=="__main__":
    topic=input("\n Enter the topic:")
    run_research_pipeline(topic)







